from __future__ import annotations

import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from config import (
    ROBOTS_URL,
    USER_AGENT,
    REQUEST_TIMEOUT_SECONDS,
    REQUEST_DELAY_SECONDS,
    MIN_TEXT_CHARACTERS,
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Encoding": "gzip",
}
REDIRECT_CODES = {301, 302, 303, 307, 308}


def canonical_article_url(url: str) -> str | None:
    """Allow only HTTPS article pages on en.wikibooks.org; strip query/fragment."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        if parsed.netloc.lower() != "en.wikibooks.org":
            return None
        if not parsed.path.startswith("/wiki/"):
            return None

        blocked = (
            "/wiki/Special:", "/wiki/Help:", "/wiki/Talk:", "/wiki/User:",
            "/wiki/Wikibooks:", "/wiki/MediaWiki:", "/wiki/Category:",
        )
        if parsed.path.startswith(blocked):
            return None
        return urlunparse(("https", "en.wikibooks.org", parsed.path, "", "", ""))
    except (TypeError, ValueError):
        return None


def load_robots(session: requests.Session):
    """Fail closed: do not fetch article pages if robots.txt cannot be checked."""
    response = session.get(
        ROBOTS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(ROBOTS_URL)
    parser.parse(response.text.splitlines())
    return parser, response.text


def extract_page(html: str, url: str) -> dict | None:
    """Extract readable article content and omit common page/navigation chrome."""
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("#firstHeading") or soup.find("title")
    title = title_el.get_text(" ", strip=True) if title_el else url

    content = soup.select_one("#mw-content-text") or soup.find("main") or soup.body
    if content is None:
        return None

    for element in content.select(
        "script, style, nav, .navbox, .mw-editsection, .metadata, "
        ".ambox, table.navbox, sup.reference, .reference"
    ):
        element.decompose()

    paragraphs = []
    for element in content.select("h1, h2, h3, h4, p, li"):
        text = " ".join(element.get_text(" ", strip=True).split())
        if text and len(text) > 25:
            paragraphs.append(text)

    page_text = "\n".join(paragraphs)
    if len(page_text) < MIN_TEXT_CHARACTERS:
        return None

    return {
        "url": url,
        "title": title,
        "text": page_text,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "characters": len(page_text),
        "word_count": len(page_text.split()),
    }


def _get_candidate(
    session: requests.Session,
    start_url: str,
    robots: urllib.robotparser.RobotFileParser,
) -> tuple[requests.Response | None, str, str]:
    """Fetch one permitted article while checking every redirect before following it."""
    current_url = start_url
    for _ in range(4):
        if not robots.can_fetch(USER_AGENT, current_url):
            return None, current_url, "ROBOTS DISALLOW (including redirect target)"
        time.sleep(REQUEST_DELAY_SECONDS)
        response = session.get(
            current_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        if response.status_code not in REDIRECT_CODES:
            return response, current_url, ""
        location = response.headers.get("Location")
        if not location:
            return response, current_url, "Redirect response did not contain Location"
        next_url = canonical_article_url(urljoin(current_url, location))
        if not next_url:
            return None, current_url, "Redirect target is outside the article scope"
        if not robots.can_fetch(USER_AGENT, next_url):
            return None, next_url, "Redirect target is disallowed by robots.txt"
        current_url = next_url
    return None, current_url, "Too many redirects; request stopped"


def crawl(seed_urls: list[str], max_pages: int, output_dir: Path):
    """Fetch a small candidate list politely and record each crawl decision."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "crawl_log.txt"
    collected = []
    log_lines = [
        f"CivilRAG crawl started UTC: {datetime.now(timezone.utc).isoformat()}",
        f"User-Agent: {USER_AGENT}",
    ]

    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        robots, robots_text = load_robots(session)
        (output_dir / "robots_snapshot.txt").write_text(
            robots_text, encoding="utf-8"
        )
        log_lines.append(f"Fetched robots.txt: {ROBOTS_URL}")
    except Exception as exc:
        log_lines.append(
            "STOPPED: Could not verify robots.txt; no article pages were requested. "
            f"Reason: {type(exc).__name__}: {exc}"
        )
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
        return collected, log_lines

    seen = set()
    for raw_url in seed_urls:
        if len(collected) >= max(1, int(max_pages)):
            break

        url = canonical_article_url(raw_url)
        if not url:
            log_lines.append(f"SKIP invalid/out-of-scope URL: {raw_url}")
            continue
        if url in seen:
            log_lines.append(f"SKIP duplicate URL: {url}")
            continue
        seen.add(url)

        if not robots.can_fetch(USER_AGENT, url):
            log_lines.append(f"ROBOTS DISALLOW — skipped without request: {url}")
            continue

        try:
            response, final_url, issue = _get_candidate(session, url, robots)
            if issue:
                log_lines.append(f"SKIP: {issue}: {final_url}")
                continue
            if response is None:
                log_lines.append(f"SKIP: no response for {url}")
                continue

            if response.status_code == 429:
                log_lines.append(
                    f"STOPPED on HTTP 429 (rate limited): {final_url}; no further article requests."
                )
                break
            if response.status_code >= 500:
                log_lines.append(
                    f"STOPPED on HTTP {response.status_code} server error: {final_url}."
                )
                break
            if response.status_code != 200:
                log_lines.append(f"SKIP HTTP {response.status_code}: {final_url}")
                continue
            if "text/html" not in response.headers.get("Content-Type", "").lower():
                log_lines.append(f"SKIP non-HTML response: {final_url}")
                continue

            page = extract_page(response.text, final_url)
            if page:
                collected.append(page)
                log_lines.append(
                    f"OK | {page['title']} | {page['word_count']} words | {final_url}"
                )
            else:
                log_lines.append(f"SKIP insufficient extractable text: {final_url}")

        except requests.RequestException as exc:
            log_lines.append(f"REQUEST ERROR: {url} | {type(exc).__name__}: {exc}")
        except Exception as exc:
            log_lines.append(f"ERROR: {url} | {type(exc).__name__}: {exc}")

    log_lines.append(f"Finished. Pages collected: {len(collected)}")
    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    return collected, log_lines

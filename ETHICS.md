# Ethical and Legal Checklist — CivilRAG

CivilRAG is a small educational Web Data Mining project based on public Wikibooks articles. It is designed for a low-volume classroom demonstration, not for high-volume harvesting.

## Protections implemented
- Fetch the current `https://en.wikibooks.org/robots.txt` before requesting any article.
- Stop without article requests if robots.txt cannot be fetched.
- Check every candidate article URL with Python's `RobotFileParser.can_fetch`.
- Restrict article requests to canonical `/wiki/` pages on `en.wikibooks.org`.
- Use a descriptive User-Agent identifying this student project.
- Wait two seconds between article requests and configure request timeouts.
- Stop on HTTP 429 (rate limiting) or HTTP 5xx server errors.
- Skip URLs that redirect outside the allowed domain or to a disallowed path.
- Store source URLs and collection metadata.
- Display source links with retrieved text.

## Important limits
- robots.txt is a crawler instruction, not a copyright license.
- Public accessibility is not blanket permission to republish.
- Wikibooks text is generally available under Creative Commons Attribution-ShareAlike, but verify each page's notice and respect exceptions or third-party material.
- Before redistributing collected text, preserve attribution and meet the applicable license/share-alike terms.
- Candidate pages are not guaranteed to exist or be allowed. The live robots check decides whether a URL will be requested.
- If collection fails, inspect `data/crawl_log.txt`; never bypass a disallow rule or access restriction.

## References
- https://en.wikibooks.org/robots.txt
- https://en.wikibooks.org/wiki/Wikibooks:Copyrights
- https://wikitech.wikimedia.org/wiki/Robot_policy
- https://en.wikibooks.org/wiki/Subject:Civil_engineering

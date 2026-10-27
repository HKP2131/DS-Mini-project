# CivilRAG — Civil Engineering Question-Answering Bot

A beginner-friendly Web Data Mining mini-project using permitted Wikibooks article pages. It covers data collection, preprocessing, TF-IDF retrieval, source-linked answers, and simple visualisation.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run_crawler.py
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Push this repository to GitHub.
2. Go to https://share.streamlit.io/ and sign in with GitHub.
3. Choose this repository, branch `main`, and main file path `app.py`.
4. Click Deploy. Wait for the build logs to finish and test the resulting app URL.

The app uses TF-IDF retrieval by default and does not need a paid API key. It expects you to run `python run_crawler.py` once to populate `data/pages.json`. Streamlit's cloud filesystem is ephemeral, so a crawl performed during a build is not assumed to persist. For a cloud demo, either include a small, license-compliant dataset you have collected and attributed, or add a Streamlit startup step that performs a small robots.txt-aware crawl; do not bypass robots.txt.

## Ethical collection
- Read the current https://en.wikibooks.org/robots.txt before crawling.
- The crawler fetches robots.txt, stops if it cannot verify the rules, checks each candidate URL, uses a descriptive User-Agent and waits between requests.
- It stops on HTTP 429 or 5xx responses.
- Only crawl pages you have verified are permitted. Public access and robots.txt are not themselves a copyright license.
- Preserve source URLs and meet each page's license/attribution/share-alike terms before redistribution.

More details: [ETHICS.md](ETHICS.md).

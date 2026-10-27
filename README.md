# CivilRAG — Civil Engineering Question-Answering Bot

CivilRAG is a Web Data Mining mini-project for Civil Engineering study questions. It checks Wikibooks' current `robots.txt`, performs a small bounded crawl inside selected Civil Engineering books, extracts and chunks text, retrieves evidence with hybrid lexical search, and provides source-linked answers plus collection visualisation. The interface keeps results visible across reruns, offers example questions, supports retrying a failed collection, and provides a source-sentence fallback when no AI key is set.

## Cloud deployment: Streamlit Community Cloud

This repository is prepared for Streamlit Community Cloud. When the app starts without `data/pages.json`, it tries a small robots.txt-aware crawl and builds the collection in the cloud runtime.

1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Choose **Create app**.
3. Set repository to `HKP2131/DS-Mini-project`, branch to `main`, and main file path to `app.py`.
4. Click **Deploy** and wait for installation and startup.
5. Open the Streamlit URL it assigns and test a question.

A public live app URL does not exist until the deployment has succeeded. The one-time Streamlit authorization/deploy action must be completed in your account. Streamlit's free Community Cloud service is documented at https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy.

## Enable generated answers (free-tier Gemini API)

The app works without any key in source-passage retrieval mode. To let Gemini synthesize a response grounded in retrieved excerpts:

1. Get a Gemini API key from https://aistudio.google.com/apikey.
2. Open the deployed app's Streamlit Community Cloud settings and select **Secrets**.
3. Add this TOML line, replacing the placeholder with your key:
   ```toml
   GEMINI_API_KEY = "your-real-key"
   ```
4. Save secrets and reboot/redeploy the app if prompted.

Do not paste a real API key in this README or commit it to GitHub. The repository includes `.streamlit/secrets.toml.example` as a format reference. Gemini's model availability and free-tier limits depend on Google's current terms and quota; check https://ai.google.dev/gemini-api/docs/pricing. If no key is configured or the API limit is reached, the bot falls back to retrieved evidence passages.

## Local run (optional)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run_crawler.py
streamlit run app.py
```

## Project pipeline

1. **Collection:** small, low-volume fetches of candidate Wikibooks pages.
2. **Ethical checks:** fetch current `robots.txt`, skip disallowed pages, identify the crawler, wait between requests, use timeouts, and stop on HTTP 429/server errors.
3. **Preprocessing:** remove page chrome, extract text, and split text into overlapping chunks.
4. **Mining / retrieval:** TF-IDF vectors and cosine similarity return relevant excerpts.
5. **Answering:** optional Gemini API synthesizes a response from the retrieved excerpts only.
6. **Visualisation:** show collected pages and a word-count chart.
7. **Attribution:** each retrieved excerpt is linked to its original Wikibooks page.

## Ethical conditions

- The seed list contains candidate pages only. Runtime rules and HTTP responses determine which pages are collected.
- If `robots.txt` cannot be fetched, the crawler stops rather than guessing.
- Public access and robots.txt do not automatically grant copyright permission.
- Verify each page's license and retain attribution/share-alike conditions before redistributing source text.
- If no pages are collected, inspect `data/crawl_log.txt`; never bypass disallow rules or access restrictions.

Read [ETHICS.md](ETHICS.md) and the current [Wikibooks robots.txt](https://en.wikibooks.org/robots.txt) before using the crawler.

## Main files

- `app.py` — polished Streamlit UI, persistent results, source-linked answer, and optional Gemini-generated answers
- `config.py` — candidate URLs and crawl limits
- `run_crawler.py` — local crawler entry point
- `src/crawler.py` — robots-aware fetch and extraction
- `src/pipeline.py` — chunking, TF-IDF retrieval, and CSV/JSON outputs
- `tests/test_civilrag.py` — offline smoke tests
- `.github/workflows/ci.yml` — automated compile and test checks
- `ETHICS.md` — ethical/legal note
- `requirements.txt` — Python dependencies

# CivilRAG — Civil Engineering Question-Answering Bot

CivilRAG is a small Web Data Mining project that collects a limited set of publicly accessible Wikibooks educational pages, extracts and preprocesses their text, retrieves relevant passages with TF-IDF, and displays source-linked results and a collection chart.

**Default mode is free and needs no paid API key.** It is an evidence-retrieval bot: it shows relevant source passages rather than claiming to generate an LLM answer. The architecture can be extended with a free-tier or local LLM later.

## Cloud demo: Streamlit Community Cloud

The application is prepared for Streamlit Community Cloud. On a fresh deployment, if `data/pages.json` is not present, the app checks the current Wikibooks `robots.txt` and attempts a small crawl from its predefined candidate article list. It saves the extracted data in the app's runtime filesystem and builds the retrieval index when it launches.

1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Click **Create app**.
3. Select repository `HKP2131/DS-Mini-project`, branch `main`, and main file path `app.py`.
4. Click **Deploy** and wait for the build to finish.
5. Open the public Streamlit URL and test a question.

Deployment requires your one-time authorization of Streamlit Community Cloud to access the GitHub repository. This repository alone is not a public live app until deployment succeeds. The cloud filesystem may be reset when the app restarts, so a fresh startup may crawl again.

## Local run (optional)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run_crawler.py
streamlit run app.py
```

## What the project demonstrates

1. **Collection:** low-volume crawling of Wikibooks article pages.
2. **Ethics:** fetch and parse the current `robots.txt`; skip disallowed URLs; use an identifying User-Agent; wait between requests; stop on HTTP 429 or server errors.
3. **Preprocessing:** HTML text extraction, basic cleaning, and overlapping word chunks.
4. **Mining:** TF-IDF vectors and cosine similarity to retrieve relevant text.
5. **Visualisation:** collection table and word-count chart.
6. **Evidence:** show the original source URL with each retrieved passage.

## Important ethical conditions

- The seed URL list only contains candidate pages; availability and permission are checked at runtime.
- If `robots.txt` cannot be fetched, the crawler stops rather than guessing.
- Public access and robots.txt do not, by themselves, grant permission to republish content.
- Check each page's licensing notice and preserve attribution/share-alike conditions before redistributing collected text.
- Do not disable the robots check if zero pages are collected. Inspect the crawl log instead.

Read [ETHICS.md](ETHICS.md) and the current [Wikibooks robots.txt](https://en.wikibooks.org/robots.txt) before running or submitting the project.

## Project files

- `app.py` — Streamlit app, question search and visualisation
- `config.py` — candidate URL list and polite crawl settings
- `run_crawler.py` — local crawler entry point
- `src/crawler.py` — robots-aware fetch and text extraction
- `src/pipeline.py` — chunking, TF-IDF retrieval and output files
- `ETHICS.md` — ethical and licensing notes
- `requirements.txt` — Python dependencies

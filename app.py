from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from config import MAX_PAGES, SEED_URLS, TOP_K
from src.crawler import crawl
from src.pipeline import Retriever, prepare_chunks, save_collection

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PAGES_FILE = DATA_DIR / "pages.json"

st.set_page_config(page_title="CivilRAG | Civil Engineering Study Bot", page_icon="🏗️", layout="wide")

def load_pages() -> list[dict]:
    if not PAGES_FILE.exists():
        return []
    try:
        value = json.loads(PAGES_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []

st.title("🏗️ CivilRAG")
st.caption("Civil Engineering study bot powered by permitted Wikibooks article pages. Retrieved passages include source links.")

pages = load_pages()

# A fresh Streamlit Cloud deployment has no locally-generated data file.
# In that case, run the small robots.txt-aware crawl when the app starts.
if not PAGES_FILE.exists() and not st.session_state.get("startup_crawl_attempted", False):
    st.session_state.startup_crawl_attempted = True
    with st.spinner("Checking Wikibooks robots.txt and collecting permitted article pages. Please wait…"):
        pages, _ = crawl(SEED_URLS, MAX_PAGES, DATA_DIR)
        save_collection(pages, prepare_chunks(pages), DATA_DIR)
    st.rerun()

if not pages:
    st.error("No article text is available. The crawl may have found no permitted or usable pages.")
    log_path = DATA_DIR / "crawl_log.txt"
    with st.expander("View crawl log"):
        st.code(log_path.read_text(encoding="utf-8") if log_path.exists() else "No crawl log available.")
    st.markdown("[Wikibooks Civil Engineering](https://en.wikibooks.org/wiki/Subject:Civil_engineering) · [robots.txt](https://en.wikibooks.org/robots.txt)")
    st.stop()

chunks = prepare_chunks(pages)
retriever = Retriever(chunks)

with st.sidebar:
    st.header("Collection overview")
    st.metric("Pages collected", len(pages))
    st.metric("Text chunks", len(chunks))
    st.metric("Words collected", sum(int(page.get("word_count", 0)) for page in pages))
    st.markdown("**Web mining pipeline**")
    st.write("1. robots.txt-aware collection")
    st.write("2. HTML extraction")
    st.write("3. Cleaning and chunking")
    st.write("4. TF-IDF retrieval")
    st.write("5. Source-linked results")
    st.caption("The first cloud startup collects a small set of permitted pages.")

st.subheader("Ask a Civil Engineering question")
question = st.text_input("Your question", placeholder="e.g., Explain soil mechanics")
top_k = st.slider("Number of source passages", min_value=1, max_value=6, value=TOP_K)

if st.button("Find information", type="primary") and question.strip():
    results = retriever.search(question, top_k=top_k)
    if not results:
        st.info("No strong text match was found. Try a different question or keyword.")
    else:
        st.markdown("### Relevant information")
        st.caption("This no-key version uses TF-IDF to retrieve evidence passages. It does not invent an answer when no source match is found.")
        for number, item in enumerate(results, start=1):
            st.markdown(f"**Passage {number}: {item['title']}** · similarity {item['score']:.3f}")
            st.write(item["text"])
            st.markdown(f"[Open original Wikibooks source]({item['url']})")
            st.divider()

st.subheader("Collected pages")
summary = pd.DataFrame([
    {
        "Title": page.get("title", ""),
        "Words": int(page.get("word_count", 0)),
        "Characters": int(page.get("characters", 0)),
        "Source": page.get("url", ""),
    }
    for page in pages
])
st.dataframe(summary, use_container_width=True, hide_index=True)

st.subheader("Collection visualisation")
fig, ax = plt.subplots()
ax.bar(summary["Title"].astype(str), summary["Words"])
ax.set_ylabel("Words collected")
ax.set_xlabel("Article")
ax.set_title("Words collected per Wikibooks page")
ax.tick_params(axis="x", labelrotation=35)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

with st.expander("Ethical crawling log"):
    log_path = DATA_DIR / "crawl_log.txt"
    st.code(log_path.read_text(encoding="utf-8") if log_path.exists() else "No crawl log found.")

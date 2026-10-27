from pathlib import Path
from config import SEED_URLS, MAX_PAGES
from src.crawler import crawl
from src.pipeline import prepare_chunks, save_collection

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

if __name__ == "__main__":
    print("CivilRAG: checking current robots.txt before article requests.")
    pages, logs = crawl(SEED_URLS, MAX_PAGES, DATA_DIR)
    chunks = prepare_chunks(pages)
    save_collection(pages, chunks, DATA_DIR)
    print("\n".join(logs))
    print(f"\nCollected pages: {len(pages)}")
    print(f"Chunks created: {len(chunks)}")
    if not pages:
        print("No pages collected. Review data/crawl_log.txt; never bypass robots.txt.")

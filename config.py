"""Settings for CivilRAG's small, robots.txt-aware Wikibooks crawl."""

SITE_ROOT = "https://en.wikibooks.org"
ROBOTS_URL = f"{SITE_ROOT}/robots.txt"

# These are candidate public article pages identified from the Wikibooks
# Civil Engineering subject page. Every candidate is checked against robots.txt
# at runtime; candidates are not assumed to be allowed or available.
SEED_URLS = [
    "https://en.wikibooks.org/wiki/Subject:Civil_engineering",
    "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation",
    "https://en.wikibooks.org/wiki/Drinking_Water",
    "https://en.wikibooks.org/wiki/House_Construction",
    "https://en.wikibooks.org/wiki/Advanced_Structural_Analysis",
    "https://en.wikibooks.org/wiki/Soil_Mechanics",
    "https://en.wikibooks.org/wiki/Fundamental_Specifications_for_Steel_Construction",
    "https://en.wikibooks.org/wiki/Environmental_Health_Engineering_Theory_and_Practice",
    "https://en.wikibooks.org/wiki/Seismic_Fitness",
    "https://en.wikibooks.org/wiki/Building_Services",
]

MAX_PAGES = 10
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = (
    "CivilRAGStudentProject/1.0 "
    "(educational Web Data Mining project; source: "
    "https://github.com/HKP2131/DS-Mini-project)"
)
MIN_TEXT_CHARACTERS = 350
CHUNK_WORDS = 180
CHUNK_OVERLAP_WORDS = 35
TOP_K = 4

# Optional local Ollama integration is disabled by default and is not needed
# for the cloud demo. The default app uses transparent TF-IDF retrieval.
USE_OLLAMA = False
OLLAMA_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/generate"

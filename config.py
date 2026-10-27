"""Configuration for a small, ethical Wikibooks Civil Engineering crawl."""

SITE_ROOT = "https://en.wikibooks.org"
ROBOTS_URL = f"{SITE_ROOT}/robots.txt"

# Candidate article pages are selected from Wikibooks' Civil Engineering books.
# The crawler checks the live robots.txt before fetching each candidate.
SEED_URLS = [
    "https://en.wikibooks.org/wiki/Subject:Civil_engineering",
    "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation",
    "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation/Introduction",
    "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation/Traffic_Flow",
    "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation/Sight_Distance",
    "https://en.wikibooks.org/wiki/Soil_Mechanics",
    "https://en.wikibooks.org/wiki/House_Construction",
    "https://en.wikibooks.org/wiki/House_Construction/Structural_building",
    "https://en.wikibooks.org/wiki/Advanced_Structural_Analysis",
    "https://en.wikibooks.org/wiki/Environmental_Health_Engineering_Theory_and_Practice",
]

# Link discovery is restricted to these civil-engineering books so crawling
# does not wander across unrelated Wikibooks content.
ALLOWED_ARTICLE_PREFIXES = [
    "/wiki/Subject:Civil_engineering",
    "/wiki/Applied_Ecology",
    "/wiki/Fundamentals_of_Transportation",
    "/wiki/Transportation_Economics",
    "/wiki/Soil_Mechanics",
    "/wiki/House_Construction",
    "/wiki/Advanced_Structural_Analysis",
    "/wiki/Environmental_Health_Engineering_Theory_and_Practice",
    "/wiki/Building_Services",
    "/wiki/Seismic_Fitness",
    "/wiki/Fundamental_Specifications_for_Steel_Construction",
]

MAX_PAGES = 8
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = (
    "CivilRAGStudentProject/1.1 "
    "(educational Web Data Mining project; "
    "https://github.com/HKP2131/DS-Mini-project)"
)
MIN_TEXT_CHARACTERS = 350
CHUNK_WORDS = 180
CHUNK_OVERLAP_WORDS = 35
TOP_K = 4

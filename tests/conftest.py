import os
from pathlib import Path

MAIN_DIR = Path(__file__).parent.parent

USE_TEST_DATABASES = os.getenv("USE_TEST_DATABASES", "1") == "1"

if USE_TEST_DATABASES:
    DATA_DIR = MAIN_DIR / "tests" / "data"
else:
    DATA_DIR = MAIN_DIR / "data"


os.environ.setdefault("WIKI_DB_DIR", str(DATA_DIR / "db" / "wiki"))
os.environ.setdefault("WIKI_VERSION", "8")
os.environ.setdefault("GAMES_DB", str(DATA_DIR / "db" / "games" / "v2.db"))

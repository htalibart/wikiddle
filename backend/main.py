import os
from pathlib import Path
import duckdb
from datetime import date

from fastapi import FastAPI, HTTPException, Query, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

LANGUAGES = ['en', 'fr']
MIN_NB_LINKS_FOR_TARGET = 20
MAX_NB_SEARCH_RESULTS = 30

app = FastAPI()
router = APIRouter(prefix="/api")

origins = ["https://wikiddle.com", "http://wikiddle.com"]
if os.environ.get("ENV") == "dev":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cached_daily_targets = {lang: {"id": None, "title": None, "date": None} for lang in LANGUAGES}

def get_con(lang: str) -> duckdb.DuckDBPyConnection:
    db_dir = Path(os.environ.get("WIKI_DB_DIR"))
    db_path = db_dir / lang / 'wiki.db'
    if not db_path.is_file():
        raise HTTPException(status_code=500, detail=f"Database not found: {db_path}")
    return duckdb.connect(db_path, read_only=True)

def get_daily_article_cached(lang: str):
    today = date.today()
    if _cached_daily_targets[lang]["date"] != today:
        seed = int(today.strftime("%Y%m%d"))
        con = get_con(lang)
        count = con.execute(f"SELECT COUNT(*) FROM articles WHERE nb_links >= {MIN_NB_LINKS_FOR_TARGET}").fetchone()[0]
        offset = seed % count
        row = con.execute(
            f"SELECT id, title FROM articles WHERE nb_links >= {MIN_NB_LINKS_FOR_TARGET} ORDER BY hash(CAST(id AS BIGINT) * ?) LIMIT 1 OFFSET ?",
            [seed, offset]
        ).fetchone()
        con.close()
        _cached_daily_targets[lang].update({"date": today, "id": row[0], "title": row[1]})
    return _cached_daily_targets[lang]


@router.get("/{lang}/daily-article")
@limiter.limit("10/minute")
def get_daily_article(request: Request, lang: str):
    # for debugging purposes: will be deleted
    article = get_daily_article_cached(lang)
    return {"id": article["id"], "title": article["title"]}


@router.get("/{lang}/article-id")
@limiter.limit("30/minute")
def get_article_id(request: Request, lang: str, title: str = Query(...)):
    con = get_con(lang)
    row = con.execute(
        "SELECT id FROM articles WHERE title = ?", [title]
    ).fetchone()
    con.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"id": row[0], "title": title}


@router.get("/{lang}/article-title")
@limiter.limit("300/minute")
def get_article_title(request: Request, lang: str, id: int = Query(...)):
    con = get_con(lang)
    row = con.execute(
        "SELECT title FROM articles WHERE id = ?", [id]
    ).fetchone()
    con.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {"id": id, "title": row[0]}


def get_neighbors(lang: str, article_id: int):
    con = get_con(lang)
    rows = con.execute(
        "SELECT target_id FROM links WHERE source_id = ?", [article_id]
    ).fetchall()
    return set(row[0] for row in rows)


@router.get("/{lang}/common-neighbors")
@limiter.limit("60/minute")
def get_common_neighbors_with_target(request: Request, lang: str, id: int = Query(...)):
    article = get_daily_article_cached(lang)
    n1 = get_neighbors(lang, article["id"])
    n2 = get_neighbors(lang, id)
    common = n1 & n2
    is_target = (article["id"] == id)
    return {
        "common": [get_article_title(request, lang, i)["title"] for i in common],
        "is_target": is_target,
    }



@router.get("/{lang}/articles")
@limiter.limit("300/minute")
def search_articles(request: Request, lang: str, query: str = Query(...)):
    con = get_con(lang)
    rows = con.execute(
    f"""SELECT id, title FROM articles 
        WHERE nb_links >= {MIN_NB_LINKS_FOR_TARGET} AND title ILIKE ?
        ORDER BY CASE 
            WHEN title ILIKE ? THEN 0
            WHEN title ILIKE ? THEN 1
            ELSE 2
        END, nb_links DESC, LENGTH(title)
        LIMIT {MAX_NB_SEARCH_RESULTS}""",
    [f"%{query}%", query, f"{query}%"]
    ).fetchall()
    con.close()
    return [{"id": row[0], "title": row[1]} for row in rows]

app.include_router(router)
#app.mount("/", StaticFiles(directory=str(MAIN_DIR / "frontend"), html=True), name="frontend")

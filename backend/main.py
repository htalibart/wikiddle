import os
import duckdb
from datetime import date

from fastapi import FastAPI, HTTPException, Query, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

MIN_NB_LINKS = 20

app = FastAPI()
router = APIRouter(prefix="/api")

origins = ["https://wikiddle.com", "http://wikiddle.com", "http://116.203.197.234"]
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

_cached_daily_target = {"id": None, "title": None, "date": None}

def get_con() -> duckdb.DuckDBPyConnection:
    db_path = os.environ.get("WIKI_DB_PATH")
    return duckdb.connect(db_path, read_only=True)

def get_daily_article_cached():
    today = date.today()
    if _cached_daily_target["date"] != today:
        seed = int(today.strftime("%Y%m%d"))
        con = get_con()
        count = con.execute(f"SELECT COUNT(*) FROM articles WHERE nb_links >= {MIN_NB_LINKS}").fetchone()[0]
        offset = seed % count
        row = con.execute(
            f"SELECT id, title FROM articles WHERE nb_links >= {MIN_NB_LINKS} ORDER BY hash(CAST(id AS BIGINT) * ?) LIMIT 1 OFFSET ?",
            [seed, offset]
        ).fetchone()
        con.close()
        _cached_daily_target.update({"date": today, "id": row[0], "title": row[1]})
    return _cached_daily_target


@router.get("/daily-article")
@limiter.limit("10/minute")
def get_daily_article(request: Request):
    # for debugging purposes: will be deleted
    article = get_daily_article_cached()
    return {"id": article["id"], "title": article["title"]}


@router.get("/article-id")
@limiter.limit("30/minute")
def get_article_id(request: Request, title: str = Query(...)):
    con = get_con()
    row = con.execute(
        "SELECT id FROM articles WHERE title = ?", [title]
    ).fetchone()
    con.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"id": row[0], "title": title}


@router.get("/article-title")
@limiter.limit("300/minute")
def get_article_title(request: Request, id: int = Query(...)):
    con = get_con()
    row = con.execute(
        "SELECT title FROM articles WHERE id = ?", [id]
    ).fetchone()
    con.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {"id": id, "title": row[0]}


def get_neighbors(article_id: int):
    con = get_con()
    rows = con.execute(
        "SELECT target_id FROM links WHERE source_id = ?", [article_id]
    ).fetchall()
    return set(row[0] for row in rows)


@router.get("/common-neighbors")
@limiter.limit("60/minute")
def get_common_neighbors_with_target(request: Request, id: int = Query(...)):
    article = get_daily_article_cached()
    n1 = get_neighbors(article["id"])
    n2 = get_neighbors(id)
    common = n1 & n2
    is_target = (article["id"] == id)
    return {
        "common": [get_article_title(request, i)["title"] for i in common],
        "is_target": is_target,
    }



@router.get("/articles")
@limiter.limit("300/minute")
def search_articles(request: Request, query: str = Query(...)):
    con = get_con()
    rows = con.execute(
    f"""SELECT id, title FROM articles 
        WHERE nb_links >= {MIN_NB_LINKS} AND title ILIKE ?
        ORDER BY CASE 
            WHEN title ILIKE ? THEN 0
            WHEN title ILIKE ? THEN 1
            ELSE 2
        END, nb_links DESC, LENGTH(title)
        LIMIT 30""",
    [f"%{query}%", query, f"{query}%"]
    ).fetchall()
    con.close()
    return [{"id": row[0], "title": row[1]} for row in rows]

app.include_router(router)
#app.mount("/", StaticFiles(directory=str(MAIN_DIR / "frontend"), html=True), name="frontend")

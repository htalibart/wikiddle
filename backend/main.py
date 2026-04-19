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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_con() -> duckdb.DuckDBPyConnection:
    db_path = os.environ.get("WIKI_DB_PATH")
    return duckdb.connect(db_path, read_only=True)


@router.get("/daily-article")
@limiter.limit("10/minute")
def get_daily_article(request: Request):
    seed = int(date.today().strftime("%Y%m%d"))
    con = get_con()
    count = con.execute(f"SELECT COUNT(*) FROM articles WHERE nb_links >= {MIN_NB_LINKS}").fetchone()[0]
    offset = seed % count
    row = con.execute(
        "SELECT id, title FROM articles ORDER BY hash(CAST(id AS BIGINT) * ?) LIMIT 1 OFFSET ?",
            [seed, offset]
    ).fetchone()
    con.close()
    if row is None:
        raise HTTPException(status_code=404, detail="No articles found")
    return {"id": row[0], "title": row[1]}


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
@limiter.limit("30/minute")
def get_common_neighbors(request: Request, id1: int = Query(...), id2: int = Query(...)):
    n1 = get_neighbors(id1)
    n2 = get_neighbors(id2)
    c = n1 & n2
    if not n1 or not n2:
        jaccard = 0.0
    else:
        jaccard = len(c) / len(n1 | n2)
    return {"common": [get_article_title(request, id_)["title"] for id_ in c], "jaccard": jaccard}


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

import os
from pathlib import Path
import duckdb
from datetime import date, timedelta
import random
import secrets

from fastapi import FastAPI, HTTPException, Query, APIRouter, Request, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

LANGUAGES = {"en", "fr"}
MIN_NB_LINKS_FOR_TARGET = 20
MIN_ARTICLE_LENGTH_FOR_TARGET = 7_000
MAX_NB_SEARCH_RESULTS = 30
MAX_TITLE_LENGTH = 300

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
_cached_yesterday_targets = {lang: {"id": None, "title": None, "date": None} for lang in LANGUAGES}


def format_date(d: date) -> str:
    """formats date in YYYY-MM-DD format"""
    return d.isoformat()


def valid_date(date_str: str) -> str:
    """validates that @date_str is in isoformat, raises 400 if not, otherwise returns the date"""
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Incorrect date format: {date_str} (should be isoformat: YYYY-MM-DD)"
        )
    return date_str


def valid_lang(lang: str) -> str:
    """validates that @lang is a supported language, raises 400 if not, otherwise returns the language"""
    if lang not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Language not supported: {lang}")
    return lang


def get_schema_version(con: duckdb.DuckDBPyConnection) -> int:
    """get schema database version (introduced categories in v2)"""
    try:
        row = con.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
    except duckdb.CatalogException:
        return 1
    return int(row[0])


def open_games_db_con() -> duckdb.DuckDBPyConnection:
    """opens a DuckDB connection to the games stats database, raises 500 if database file is not found"""
    db_path = os.environ.get("GAMES_DB")
    if db_path is None:
        raise HTTPException(status_code=500, detail="GAMES_DB environment variable is not set")
    db_path = Path(db_path)
    if not db_path.is_file():
        raise HTTPException(status_code=500, detail=f"Database not found: {db_path}")
    return duckdb.connect(db_path)


def open_wiki_db_con(lang: str) -> duckdb.DuckDBPyConnection:
    """opens a DuckDB connection to the appropriate database depending on language, raises 500 if database file is not found"""
    db_dir = os.environ.get("WIKI_DB_DIR")
    db_version = os.environ.get("WIKI_VERSION")
    if db_dir is None:
        raise HTTPException(status_code=500, detail="WIKI_DB_DIR environment variable is not set")
    if db_version is None:
        raise HTTPException(status_code=500, detail="WIKI_VERSION environment variable is not set")
    db_path = Path(db_dir) / f"v{db_version}" / f"{lang}.db"
    if not db_path.is_file():
        raise HTTPException(status_code=500, detail=f"Database not found: {db_path}")
    return duckdb.connect(db_path, read_only=True)


def get_wiki_db_con(lang: str = Depends(valid_lang)):
    """FastAPI dependency to yield a DuckDB connection to the wiki database for the given language, closes it after the request"""
    con = open_wiki_db_con(lang)
    try:
        yield con
    finally:
        con.close()


def get_games_db_con():
    """FastAPI dependency to yield a DuckDB connection to the games database, closes it after the request"""
    con = open_games_db_con()
    try:
        yield con
    finally:
        con.close()


def get_article_from_date(lang: str, d: date) -> dict:
    """returns article from a previous game given language and date"""
    con = open_games_db_con()
    date_str = format_date(d)
    try:
        row = con.execute(
            "SELECT article_id, article_title FROM daily_articles WHERE date = ? AND lang = ?", [date_str, lang]
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"No article found at {date_str} in {lang} database")
    finally:
        con.close()
    return {"date": d, "id": row[0], "title": row[1]}


def add_article_to_games_db(day: date, lang: str, article_id: int, article_title: str):
    """add new article to previous games database"""
    con = open_games_db_con()
    try:
        con.execute(
            "INSERT OR IGNORE INTO daily_articles VALUES (?, ?, ?, ?)",
            [format_date(day), lang, article_id, article_title],
        )
    finally:
        con.close()


def get_yesterdays_article_cached(lang: str) -> dict:
    """returns yesterday's article for the given language, refreshes the cache if needed"""
    yesterday = date.today() - timedelta(days=1)
    if _cached_yesterday_targets[lang]["date"] != yesterday:
        _cached_yesterday_targets[lang].update(get_article_from_date(lang, yesterday))
    return _cached_yesterday_targets[lang]


def get_daily_article_filter(schema_version: int, temp_relax=False) -> str:
    """return SQL filter for the daily article choice"""
    if schema_version == 1:
        return f"nb_links >= {MIN_NB_LINKS_FOR_TARGET}"
    elif schema_version >= 2:
        if temp_relax:
            return f"nb_links >= {MIN_NB_LINKS_FOR_TARGET} AND is_target_candidate IS TRUE"
        else:
            return f"nb_links >= {MIN_NB_LINKS_FOR_TARGET} AND is_target_candidate IS TRUE AND article_length >= {MIN_ARTICLE_LENGTH_FOR_TARGET}"
    raise ValueError(f"Unsupported schema version: {schema_version}")


def get_daily_article_cached(lang: str) -> dict:
    """returns today's daily article for the given language, refreshes the cache if needed"""
    today = date.today()

    # if cache is stale, update it
    if _cached_daily_targets[lang]["date"] != today:
        # first, try games database
        try:
            article = get_article_from_date(lang, today)
        except HTTPException as e:
            if e.status_code != 404:
                raise
            # if daily article is not in games database, create it
            seed = int(today.strftime("%Y%m%d"))
            con = open_wiki_db_con(lang)
            schema_version = get_schema_version(con)
            article_filter = get_daily_article_filter(schema_version)
            try:
                count = con.execute(f"SELECT COUNT(*) FROM articles WHERE {article_filter}").fetchone()[0]
                offset = seed % count
                row = con.execute(
                    f"SELECT id, title FROM articles WHERE {article_filter} ORDER BY hash(CAST(id AS BIGINT) * ?) LIMIT 1 OFFSET ?",
                    [seed, offset],
                ).fetchone()
                article = {"date": today, "id": row[0], "title": row[1]}
                add_article_to_games_db(
                    day=article["date"], lang=lang, article_id=article["id"], article_title=article["title"]
                )
            finally:
                con.close()
        _cached_daily_targets[lang].update(article)
    return _cached_daily_targets[lang]


@router.get("/{lang}/yesterdays-article")
@limiter.limit("10/minute")
def get_yesterdays_article(request: Request, lang: str = Depends(valid_lang)):
    article = get_yesterdays_article_cached(lang)
    return {"id": article["id"], "title": article["title"]}


@router.get("/{lang}/daily-article")
@limiter.limit("10/minute")
def get_daily_article(request: Request, lang: str = Depends(valid_lang)):
    # for debugging purposes: will be deleted
    article = get_daily_article_cached(lang)
    return {"id": article["id"], "title": article["title"]}


@router.get("/{lang}/article-id")
@limiter.limit("30/minute")
def get_article_id(
    request: Request, con=Depends(get_wiki_db_con), title: str = Query(..., min_length=1, max_length=MAX_TITLE_LENGTH)
):
    row = con.execute("SELECT id FROM articles WHERE title = ?", [title]).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"id": row[0], "title": title}


def get_article_titles(lang: str, ids: set[int]):
    """returns the titles of the articles for language @lang with given ids @ids"""
    if not ids:
        return []
    con = open_wiki_db_con(lang)
    try:
        rows = con.execute("SELECT title FROM articles WHERE id IN (SELECT * FROM UNNEST(?))", [list(ids)]).fetchall()
        return [row[0] for row in rows]
    finally:
        con.close()


@router.get("/{lang}/article-title")
@limiter.limit("300/minute")
def get_article_title(request: Request, lang: str = Depends(valid_lang), id: int = Query(...)):
    titles = get_article_titles(lang, {id})
    if not titles:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"id": id, "title": titles[0]}


def get_links(lang: str, article_id: int) -> dict:
    """returns a dict {id: title} articles that article with id @article_id links to in language @lang"""
    con = open_wiki_db_con(lang)
    try:
        rows = con.execute(
            "SELECT l.target_id, p.title FROM links l JOIN articles p ON l.target_id = p.id WHERE l.source_id = ?",
            [article_id],
        ).fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        con.close()


def get_categories(lang: str, article_id: int) -> dict:
    """returns a dict {id: title} of categories that article @article_id belongs to in language @lang"""
    con = open_wiki_db_con(lang)
    try:
        rows = con.execute(
            "SELECT ac.category_id, c.name FROM article_categories ac JOIN categories c ON ac.category_id = c.id WHERE ac.article_id = ?",
            [article_id],
        ).fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        con.close()


@router.get("/{lang}/common-info")
@limiter.limit("60/minute")
def get_common_info_with_target(request: Request, lang: str = Depends(valid_lang), id: int = Query(...)):
    """API route to get the links and categories that are common to the user guess and the target article"""
    article = get_daily_article_cached(lang)

    # common links
    links1 = get_links(lang, article["id"])
    links2 = get_links(lang, id)
    common_links = set(links1.keys()) & set(links2.keys())

    # common categories
    cats1 = get_categories(lang, article["id"])
    cats2 = get_categories(lang, id)
    common_cats = set(cats1.keys()) & set(cats2.keys())

    is_target = article["id"] == id
    is_on_target = id in links1
    return {
        "common_links": [links1[lid] for lid in common_links],
        "common_categories": [cats1[cid] for cid in common_cats],
        "is_target": is_target,
        "is_on_target": is_on_target,
        "game_date": format_date(article["date"]),
    }


@router.get("/{lang}/articles")
@limiter.limit("300/minute")
def search_articles(
    request: Request, con=Depends(get_wiki_db_con), query: str = Query(..., min_length=1, max_length=MAX_TITLE_LENGTH)
):
    """API route to search in the database (called by TomSelect)"""
    schema_version = get_schema_version(con)
    article_filter = get_daily_article_filter(schema_version, temp_relax=True)
    rows = con.execute(
        f"""SELECT id, title FROM articles 
        WHERE {article_filter} AND title ILIKE ?
        ORDER BY CASE 
            WHEN title ILIKE ? THEN 0
            WHEN title ILIKE ? THEN 1
            ELSE 2
        END, nb_links DESC, LENGTH(title)
        LIMIT {MAX_NB_SEARCH_RESULTS}""",
        [f"%{query}%", query, f"{query}%"],
    ).fetchall()
    return [{"id": row[0], "title": row[1]} for row in rows]


@router.post("/{lang}/new-target-link")
@limiter.limit("300/minute")
def get_one_new_link(request: Request, lang: str = Depends(valid_lang), known_titles: list = Body(default=[])):
    """API route to get one random link target that was not already found"""
    target = get_daily_article_cached(lang)
    link_ids = get_links(lang, target["id"])
    link_titles = set(get_article_titles(lang, link_ids))
    n_not_guessed = link_titles.difference(set(known_titles))
    game_date = format_date(target["date"])
    if not n_not_guessed:
        return {"title": None, "game_date": game_date}
    hint_title = random.choice(list(n_not_guessed))
    return {"title": hint_title, "game_date": game_date}


@router.get("/{lang}/game-date")
@limiter.limit("10/minute")
def get_game_date(request: Request, lang: str = Depends(valid_lang)):
    """API route to get the date of the current cached game"""
    article = get_daily_article_cached(lang)
    return {"date": format_date(article["date"])}


@router.post("/admin/refresh", include_in_schema=False)
@limiter.limit("5/minute")
def refresh_daily_articles(request: Request, authorization: str = Header(default=None)):
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

    if not ADMIN_TOKEN or authorization is None:
        raise HTTPException(status_code=403, detail="Forbidden")

    expected = f"Bearer {ADMIN_TOKEN}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=403, detail="Forbidden")

    for lang in LANGUAGES:
        get_daily_article_cached(lang)
    return {"status": "ok"}


@router.get("/admin/{lang}/version", include_in_schema=False)
@limiter.limit("10/minute")
def get_db_version(request: Request, con=Depends(get_wiki_db_con)):
    return {"schema_version": get_schema_version(con)}


app.include_router(router)

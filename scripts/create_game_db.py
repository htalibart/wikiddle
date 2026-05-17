import os
from pathlib import Path
import sys
import duckdb
from datetime import date, timedelta

MAIN_DIR = Path(os.path.realpath(__file__)).parent.parent
sys.path.insert(0, str(MAIN_DIR / 'backend'))

from main import format_date, open_wiki_db_con, MIN_NB_LINKS_FOR_TARGET

def get_one_article(lang: str, d: date) -> dict:
    seed = int(d.strftime("%Y%m%d"))
    con = open_wiki_db_con(lang)
    try:
        count = con.execute(f"SELECT COUNT(*) FROM articles WHERE nb_links >= {MIN_NB_LINKS_FOR_TARGET}").fetchone()[0]
        offset = seed % count
        row = con.execute(
            f"SELECT id, title FROM articles WHERE nb_links >= {MIN_NB_LINKS_FOR_TARGET} ORDER BY hash(CAST(id AS BIGINT) * ?) LIMIT 1 OFFSET ?",
            [seed, offset]
        ).fetchone()
    finally:
        con.close()
    return {"date": d, "id": row[0], "title": row[1]}


if __name__=="__main__":
    db_path = MAIN_DIR / 'data' / 'games.db' 
    os.environ["WIKI_DB_DIR"] = str(MAIN_DIR / 'data'/ 'db')

    con = duckdb.connect(db_path)

    con.execute(f"""
        CREATE TABLE IF NOT EXISTS daily_articles (
            date DATE NOT NULL,
            lang TEXT NOT NULL,
            article_id BIGINT,
            article_title TEXT NOT NULL,
            PRIMARY KEY (date, lang)
        );
    """)

    for lang in ['fr', 'en']:
        yesterday = date.today() - timedelta(days=1) 
        art = get_one_article(lang, yesterday)
        con.execute(
                "INSERT INTO daily_articles VALUES (?, ?, ?, ?)",
                [format_date(art["date"]), lang, art["id"], art["title"]]
        )

    con.close()

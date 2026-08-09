from datetime import date, timedelta
from pathlib import Path

import duckdb

GAMES_DB_FILE = Path(__file__).parent / "data" / "db" / "games" / "v2.db"


if __name__ == "__main__":
    con = duckdb.connect(str(GAMES_DB_FILE))

    try:
        rows = con.execute(
            """
            SELECT lang, article_id, article_title, wiki_db_version
            FROM daily_articles
            QUALIFY ROW_NUMBER() OVER (PARTITION BY lang ORDER BY date DESC) = 1
            """
        ).fetchall()

        con.execute("DELETE FROM daily_articles")

        today = date.today()
        new_rows = []

        for lang, article_id, article_title, wiki_db_version in rows:
            new_rows.append((today, lang, article_id, article_title, wiki_db_version))
            new_rows.append((today - timedelta(days=1), lang, article_id, article_title, wiki_db_version))

        con.executemany("INSERT INTO daily_articles VALUES (?, ?, ?, ?, ?)", new_rows)
    finally:
        con.close()

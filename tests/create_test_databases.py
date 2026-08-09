from datetime import date, timedelta
from pathlib import Path

import duckdb

MAIN_DIR = Path(__file__).parent.parent
SOURCE_WIKI_DB_DIR = MAIN_DIR / "data" / "db" / "wiki" / "v8"
TEST_WIKI_DB_DIR = MAIN_DIR / "tests" / "data" / "db" / "wiki" / "v9"
TEST_GAMES_DB_FILE = MAIN_DIR / "tests" / "data" / "db" / "games" / "v2.db"

WIKI_VERSION = 9
SEARCH_FILTER = "nb_links >= 20 AND nb_words >= 700 AND nb_backlinks >= 30"


def get_wiki_db_files(lang: str) -> tuple[Path, Path]:
    return SOURCE_WIKI_DB_DIR / f"{lang}.db", TEST_WIKI_DB_DIR / f"{lang}.db"


def create_empty_wiki_database(lang: str) -> duckdb.DuckDBPyConnection:
    src_file, dst_file = get_wiki_db_files(lang)

    if not src_file.is_file():
        raise FileNotFoundError(src_file)

    TEST_WIKI_DB_DIR.mkdir(parents=True, exist_ok=True)
    dst_file.unlink(missing_ok=True)

    dst_con = duckdb.connect(str(dst_file))
    src_path = str(src_file).replace("'", "''")
    dst_con.execute(f"ATTACH '{src_path}' AS source (READ_ONLY)")

    tables = dst_con.execute("SHOW TABLES FROM source").fetchall()

    for (table_name,) in tables:
        escaped_table_name = table_name.replace('"', '""')
        dst_con.execute(
            f'CREATE TABLE "{escaped_table_name}" AS SELECT * FROM source."{escaped_table_name}" WHERE FALSE'
        )

    dst_con.execute("INSERT INTO metadata SELECT * FROM source.metadata")
    return dst_con


def copy_articles_by_titles(dst_con: duckdb.DuckDBPyConnection, titles: list[str]) -> set[int]:
    rows = dst_con.execute(
        "SELECT id, title FROM source.articles WHERE title IN (SELECT * FROM UNNEST(?))", [titles]
    ).fetchall()

    found_titles = {title for _, title in rows}
    missing_titles = set(titles) - found_titles

    if missing_titles:
        raise RuntimeError(f"Articles not found: {sorted(missing_titles)}")

    dst_con.execute(
        """
        INSERT INTO articles
        SELECT src.*
        FROM source.articles src
        WHERE src.title IN (SELECT * FROM UNNEST(?))
          AND NOT EXISTS (SELECT 1 FROM articles dst WHERE dst.id = src.id)
        """,
        [titles],
    )

    return {article_id for article_id, _ in rows}


def copy_article_by_id(dst_con: duckdb.DuckDBPyConnection, article_id: int) -> int:
    exists = dst_con.execute("SELECT 1 FROM source.articles WHERE id = ?", [article_id]).fetchone()

    if exists is None:
        raise RuntimeError(f"Article ID not found: {article_id}")

    dst_con.execute(
        """
        INSERT INTO articles
        SELECT src.*
        FROM source.articles src
        WHERE src.id = ?
          AND NOT EXISTS (SELECT 1 FROM articles dst WHERE dst.id = src.id)
        """,
        [article_id],
    )

    return article_id


def copy_search_results(
    dst_con: duckdb.DuckDBPyConnection,
    query: str,
    limit: int = 30,
) -> set[int]:
    parameters = [f"%{query}%", query, f"{query}%", limit]

    rows = dst_con.execute(
        f"""
        SELECT id
        FROM source.articles
        WHERE {SEARCH_FILTER}
          AND title ILIKE ?
        ORDER BY CASE WHEN title ILIKE ? THEN 0 WHEN title ILIKE ? THEN 1 ELSE 2 END,
                 nb_links DESC,
                 LENGTH(title)
        LIMIT ?
        """,
        parameters,
    ).fetchall()

    dst_con.execute(
        f"""
        INSERT INTO articles
        SELECT selected.*
        FROM (
            SELECT *
            FROM source.articles
            WHERE {SEARCH_FILTER}
              AND title ILIKE ?
            ORDER BY CASE WHEN title ILIKE ? THEN 0 WHEN title ILIKE ? THEN 1 ELSE 2 END,
                     nb_links DESC,
                     LENGTH(title)
            LIMIT ?
        ) selected
        WHERE NOT EXISTS (SELECT 1 FROM articles dst WHERE dst.id = selected.id)
        """,
        parameters,
    )

    return {article_id for (article_id,) in rows}


def copy_links_and_categories(dst_con: duckdb.DuckDBPyConnection, article_ids: set[int]) -> None:
    if not article_ids:
        return

    ids = list(article_ids)

    dst_con.execute(
        """
        INSERT INTO articles
        SELECT src.*
        FROM source.articles src
        WHERE src.id IN (
            SELECT DISTINCT target_id
            FROM source.links
            WHERE source_id IN (SELECT * FROM UNNEST(?))
        )
          AND NOT EXISTS (SELECT 1 FROM articles dst WHERE dst.id = src.id)
        """,
        [ids],
    )

    dst_con.execute(
        """
        INSERT INTO links
        SELECT src.*
        FROM source.links src
        WHERE src.source_id IN (SELECT * FROM UNNEST(?))
          AND NOT EXISTS (
              SELECT 1
              FROM links dst
              WHERE dst.source_id = src.source_id AND dst.target_id = src.target_id
          )
        """,
        [ids],
    )

    dst_con.execute(
        """
        INSERT INTO categories
        SELECT src.*
        FROM source.categories src
        WHERE src.id IN (
            SELECT DISTINCT category_id
            FROM source.article_categories
            WHERE article_id IN (SELECT * FROM UNNEST(?))
        )
          AND NOT EXISTS (SELECT 1 FROM categories dst WHERE dst.id = src.id)
        """,
        [ids],
    )

    dst_con.execute(
        """
        INSERT INTO article_categories
        SELECT src.*
        FROM source.article_categories src
        WHERE src.article_id IN (SELECT * FROM UNNEST(?))
          AND NOT EXISTS (
              SELECT 1
              FROM article_categories dst
              WHERE dst.article_id = src.article_id AND dst.category_id = src.category_id
          )
        """,
        [ids],
    )


def get_article_id(con: duckdb.DuckDBPyConnection, title: str) -> int:
    row = con.execute("SELECT id FROM articles WHERE title = ?", [title]).fetchone()

    if row is None:
        raise RuntimeError(f"Article not found: {title}")

    return row[0]


def create_games_database(daily_articles: dict[str, tuple[int, str]]) -> None:
    TEST_GAMES_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_GAMES_DB_FILE.unlink(missing_ok=True)

    con = duckdb.connect(str(TEST_GAMES_DB_FILE))

    try:
        con.execute("""
            CREATE TABLE daily_articles (
                date DATE NOT NULL,
                lang TEXT NOT NULL,
                article_id BIGINT,
                article_title TEXT NOT NULL,
                wiki_db_version INTEGER,
                PRIMARY KEY (date, lang)
            )
        """)

        rows = []

        for lang, (article_id, article_title) in daily_articles.items():
            rows.append((date.today(), lang, article_id, article_title, WIKI_VERSION))
            rows.append((date.today() - timedelta(days=1), lang, article_id, article_title, WIKI_VERSION))

        con.executemany("INSERT INTO daily_articles VALUES (?, ?, ?, ?, ?)", rows)
    finally:
        con.close()


if __name__ == "__main__":
    en_con = create_empty_wiki_database("en")

    try:
        en_article_ids = copy_articles_by_titles(en_con, ["Brussels", "Daft Punk", "Justice", "Electronic music"])
        en_article_ids.update(copy_search_results(en_con, "python"))
        en_article_ids.update(copy_search_results(en_con, "a"))
        en_article_ids.add(copy_article_by_id(en_con, 12))
        copy_links_and_categories(en_con, en_article_ids)
        en_daily_article = (get_article_id(en_con, "Brussels"), "Brussels")
    finally:
        en_con.close()

    fr_con = create_empty_wiki_database("fr")

    try:
        fr_article_ids = copy_articles_by_titles(fr_con, ["Bruxelles", "Daft Punk", "Justice"])
        fr_article_ids.update(copy_search_results(fr_con, "python"))
        fr_article_ids.update(copy_search_results(fr_con, "a"))
        fr_article_ids.add(copy_article_by_id(fr_con, 12))
        copy_links_and_categories(fr_con, fr_article_ids)
        fr_daily_article = (get_article_id(fr_con, "Bruxelles"), "Bruxelles")
    finally:
        fr_con.close()

    create_games_database({"en": en_daily_article, "fr": fr_daily_article})

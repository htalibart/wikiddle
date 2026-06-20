from pathlib import Path
import shutil
import argparse
import duckdb

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent

def add_nb_backlinks(con: duckdb.DuckDBPyConnection):
    columns = con.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'articles'
    """).fetchall()
    column_names = {row[0] for row in columns}
    if "nb_backlinks" not in column_names:
        con.execute("ALTER TABLE articles ADD COLUMN nb_backlinks INTEGER DEFAULT 0")


def update_nb_backlinks(con: duckdb.DuckDBPyConnection):
    con.execute("""
        UPDATE articles
        SET nb_backlinks = backlink_counts.cnt
        FROM (
            SELECT target_id, COUNT(*) AS cnt
            FROM links
            GROUP BY target_id
        ) AS backlink_counts
        WHERE articles.id = backlink_counts.target_id
    """)


def update_metadata(con: duckdb.DuckDBPyConnection, new_version: int):
    con.execute("DELETE FROM metadata WHERE key = 'schema_version'")
    con.execute("INSERT INTO metadata VALUES ('schema_version', ?)", [str(new_version)])


def update_backlinks(wiki_db_dir: Path, old_version: int):
    new_version = old_version + 1
    src_db_file = wiki_db_dir / f"v{old_version}" / f"{lang}.db"
    dst_db_file = wiki_db_dir / f"v{new_version}" / f"{lang}.db"

    if not src_db_file.is_file():
        raise FileNotFoundError(f"Source database not found: {src_db_file}")

    if dst_db_file.is_file():
        raise FileExistsError(f"Destination database already exists: {dst_db_file}")


    print(f"Copying {src_db_file} -> {dst_db_file}...")
    dst_db_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_db_file, dst_db_file)

    con = duckdb.connect(str(dst_db_file))
    try:
        print("Adding nb_backlinks column...")
        add_nb_backlinks(con)

        print("Computing backlink counts...")
        update_nb_backlinks(con)

        print("Creating index on nb_backlinks...")
        con.execute("CREATE INDEX IF NOT EXISTS idx_nb_backlinks ON articles(nb_backlinks)")

        update_metadata(con, new_version)

        nb_articles = con.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        nb_with_backlinks = con.execute("SELECT COUNT(*) FROM articles WHERE nb_backlinks > 0").fetchone()[0]
        avg_backlinks = con.execute("SELECT AVG(nb_backlinks) FROM articles").fetchone()[0]
        max_backlinks = con.execute("SELECT MAX(nb_backlinks) FROM articles").fetchone()[0]

        print(f"Articles with at least 1 backlink: {nb_with_backlinks}/{nb_articles}")
        print(f"Average backlinks: {avg_backlinks:.1f}")
        print(f"Max backlinks: {max_backlinks}")
        print(f"Schema version updated to {new_version}")
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("lang", type=str)
    parser.add_argument("--old_version", type=int, default=2)
    args = parser.parse_args()

    lang = args.lang
    old_version = args.old_version

    wiki_db_dir = MAIN_DIR / "data" / "db" / "wiki"
    update_backlinks(wiki_db_dir, old_version) 

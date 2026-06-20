from pathlib import Path
import shutil
import duckdb


THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent


def migrate_games_db() -> None:
    games_db_dir = MAIN_DIR / "data" / "db" / "games"
    src_db_file = games_db_dir / "v1.db"
    dst_db_file = games_db_dir / "v2.db"

    dst_db_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_db_file, dst_db_file)

    con = duckdb.connect(str(dst_db_file))
    try:
        con.execute("ALTER TABLE daily_articles ADD COLUMN wiki_db_version INTEGER")
        con.execute("UPDATE daily_articles SET wiki_db_version = 2")
    finally:
        con.close()


if __name__ == "__main__":
    migrate_games_db()

from pathlib import Path
import re
import argparse
import duckdb

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent

FILTER_VERSION = 1


def keep_category_fr(c: str) -> bool:
    if c.startswith((
        "Championnat",
        "Coupe",
        "Grand Prix",
        "Ligue",
        "Match",
        "Saison",
        "Sport",
        "Tour de",
        "Tournoi",
        "Album",
        "Bataillon",
        "Canton électoral",
        "Circonscription",
        "Édition",
        "Élection ",
        "Régiment",
        "Tournée",
    )):
        return False

    if any(s in c.lower() for s in (
        "arbitre",
        "arts martiaux",
        "association des sports",
        "athlète",
        "athlétisme",
        "automobile",
        "aviron",
        "badminton",
        "basket",
        "biathlon",
        "bobeu",
        "boxe",
        "boxeu",
        "catcheur",
        "catcheuse",
        "champion",
        "chorégraphe",
        "club sportif",
        "combat sport",
        "compétition",
        "coureu",
        "course",
        "cricket",
        "cyclisme",
        "cycliste",
        "dans le sport",
        "de sport",
        "des sports",
        "du sport",
        "en sport",
        "entraîneur",
        "équipe",
        "équestre",
        "escrime",
        "événement sportif",
        "fédération sportive",
        "football",
        "formule 1",
        "futsal",
        "gardien de but",
        "golf",
        "gymnaste",
        "handball",
        "handisport",
        "hockey",
        "joueur",
        "joueuse",
        "judo",
        "karaté",
        "league",
        "lié au sport",
        "liée au sport",
        "lutte",
        "marathon",
        "médaillés aux jeux",
        "moto",
        "nage ",
        "nageu",
        "natation",
        "olympique",
        "paralympique",
        "patineur",
        "patineuse",
        "pentathlon",
        "pétanque",
        "pilote de",
        "plongeon",
        "rallye",
        "route du rhum",
        "rugby",
        "sélectionneu",
        "skieu",
        "skieur",
        "snowboard",
        "sport équestre",
        "sport hippique",
        "sportif",
        "sportive",
        "squash",
        "station de sport",
        "surf",
        "taekwond",
        "tennis",
        "tournoi",
        "triathlon",
        "união",
        "unione",
        "vainqueur",
        "voile",
        "volley",
        "vtt",
        "wrestling",
        "cérémonie",
    )):
        return False

    if re.search(r"Sport .+ \d{4}", c):
        return False
    if re.search(r"Championnat .+ \d{4}", c):
        return False
    if re.search(r"club .+sport", c, re.IGNORECASE):
        return False
    if re.search(r"centre .+sport", c, re.IGNORECASE):
        return False
    if re.search(r"\d{4} en sport", c):
        return False
    if re.search(r"\d{4}-\d{2,4} en", c):
        return False

    return True


def keep_category_en(c: str) -> bool:
    if c.startswith((
        "Championship",
        "Cup",
        "Grand Prix",
        "League",
        "Match",
        "Season",
        "Sport",
        "Tour of",
        "Tournament",
        "Album",
        "Battalion",
        "Electoral district",
        "Election ",
        "Regiment",
        "Tour ",
    )):
        return False

    if any(s in c.lower() for s in (
        "athlete",
        "athletics",
        "badminton",
        "baseball",
        "basketball",
        "biathlon",
        "boxer",
        "boxing",
        "champion",
        "championship",
        "chess player",
        "coach",
        "competition",
        "cricket",
        "cricketer",
        "cycling",
        "cyclist",
        "darts",
        "diver",
        "equestrian",
        "fencer",
        "fencing",
        "field hockey",
        "figure skater",
        "football",
        "formula one",
        "futsal",
        "golf",
        "golfer",
        "gymnast",
        "handball",
        "hockey",
        "jockey",
        "judo",
        "karate",
        "karting",
        "lacrosse",
        "league",
        "marathon",
        "martial art",
        "medalist",
        "medallist",
        "motorsport",
        "olympic",
        "paralympic",
        "pentathlon",
        "player",
        "racing",
        "rally",
        "referee",
        "rugby",
        "sailor",
        "sailing",
        "ski jumper",
        "skier",
        "snowboard",
        "sport",
        "sporting",
        "sports",
        "squash",
        "surfer",
        "swimmer",
        "swimming",
        "taekwondo",
        "tennis",
        "tournament",
        "triathlon",
        "volleyball",
        "wrestler",
        "wrestling",
        "ceremony",
    )):
        return False

    if re.search(r"Sport .+ \d{4}", c):
        return False
    if re.search(r"Championship .+ \d{4}", c):
        return False
    if re.search(r"club .+sport", c, re.IGNORECASE):
        return False
    if re.search(r"sports? club", c, re.IGNORECASE):
        return False
    if re.search(r"sports? centre", c, re.IGNORECASE):
        return False
    if re.search(r"sports? center", c, re.IGNORECASE):
        return False
    if re.search(r"\d{4} in sport", c):
        return False
    if re.search(r"\d{4} in sports", c):
        return False
    if re.search(r"\d{4}-\d{2,4} in", c):
        return False

    return True


def keep_category(lang: str, c: str) -> bool:
    if lang == "fr":
        return keep_category_fr(c)
    elif lang == 'en':
        return keep_category_en(c)
    raise NotImplementedError(lang)


def add_is_target_candidate(con: duckdb.DuckDBPyConnection):
    columns = con.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'articles'
    """).fetchall()
    column_names = {row[0] for row in columns}
    if "is_target_candidate" not in column_names:
        con.execute("ALTER TABLE articles ADD COLUMN is_target_candidate BOOLEAN")


def update_metadata(con: duckdb.DuckDBPyConnection):
    con.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    con.execute("DELETE FROM metadata WHERE key = 'category_filter_version'")
    con.execute("INSERT INTO metadata VALUES ('category_filter_version', ?)", [str(FILTER_VERSION)])


def update_is_target_candidate(db_file: Path, lang: str):
    con = duckdb.connect(str(db_file))
    try:
        add_is_target_candidate(con)

        rows = con.execute("SELECT id, name FROM categories").fetchall()
        rejected_category_ids = [
            category_id
            for category_id, category_name in rows
            if not keep_category(lang, category_name)
        ]

        con.execute("UPDATE articles SET is_target_candidate = TRUE")

        if rejected_category_ids:
            con.execute("""
                UPDATE articles
                SET is_target_candidate = FALSE
                WHERE id IN (
                    SELECT DISTINCT article_id
                    FROM article_categories
                    WHERE category_id IN (SELECT * FROM UNNEST(?))
                )
            """, [rejected_category_ids])

        update_metadata(con)

        nb_articles = con.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        nb_candidates = con.execute("SELECT COUNT(*) FROM articles WHERE is_target_candidate").fetchone()[0]
        nb_rejected_categories = len(rejected_category_ids)

        print(f"Database: {db_file}")
        print(f"Rejected categories: {nb_rejected_categories}")
        print(f"Target candidates: {nb_candidates}/{nb_articles}")
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("lang", type=str)
    parser.add_argument("--version", type=int, default=2)
    args = parser.parse_args()

    lang = args.lang
    db_file = MAIN_DIR/"data"/"db"/"wiki"/f"v{args.version}"/f"{lang}.db"

    if not db_file.is_file():
        raise FileNotFoundError(f"Database not found: {db_file}")

    update_is_target_candidate(db_file, lang)

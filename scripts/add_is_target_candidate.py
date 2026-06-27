from pathlib import Path
import re
import argparse
import duckdb
import shutil

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent

FILTER_VERSION = 2


def keep_category_fr(c: str) -> bool:
    if c.startswith((
        "Liste ",
        "Homonymie",
        "Championnat",
        "Coupe",
        "Grand Prix",
        "Ligue",
        "Match",
        "Saison",
        "Sport",
        "Tour de",
        "Tour d'",
        "Tournoi",
        "Album",
        "Discographie",
        "Récompense musicale par année",
        "Bataillon",
        "Canton électoral",
        "Circonscription",
        "Édition",
        "Élection",
        "Régiment",
        "Tournée",
        "Épisode",
        "Filmographie",
        "Chanson",
        "Gare ",
        "Station de ",
        "Autoroute",
        "Route nationale",
        "Route départementale",
        "Route dans",
        "Voie dans",
        "Voie à",
        "Cour (voie)",
        "Voie piétonnière",
        "Rue dans",
        "Canton de",
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
        "cricket",
        "cyclisme",
        "cycliste",
        "entraîneur",
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
        "marathon",
        "médaillés aux jeux",
        "moto",
        "nage ",
        "nageu",
        "natation",
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
        "arrondissement d",
        "conseil départemental",
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
    if re.search(r"\d{4} en ", c):
        return False
    if re.search(r"\d{4} à la ", c):
        return False
    if re.search(r"\d{4}-\d{2,4} en", c):
        return False

    MONTHS_FR_PATTERN = r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)"
    if re.search(r"^" + MONTHS_FR_PATTERN + r" en ", c, re.IGNORECASE):
        return False

    return True


def keep_category_en(c: str) -> bool:
    if c.startswith((
        "Lists",
        "Disambiguation",
        "Championship",
        "Cup ",
        "Grand Prix",
        "Match",
        "Tour of",
        "Tournament",
        "Album",
        "Discography",
        "Battalion",
        "Electoral district",
        "Election ",
        "Regiment",
        "Television episodes",
        "Railway stations",
        "Autoroutes",
        "Streets in",
        "Canton of",
        "Cantons of",
        "Districts of",
    )):
        return False

    if c.endswith((
        "songs",
    )):
        return False


    if any(s in c.lower() for s in (
        "athlete",
        "badminton",
        "baseball",
        "basketball",
        "biathlon",
        "boxer",
        "boxing",
        "championship",
        "chess player",
        "cricket",
        "cricketer",
        "darts",
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
        "martial art",
        "medalist",
        "medallist",
        "motorsport",
        "paralympic",
        "pentathlon",
        "racing",
        "rugby",
        "sailor",
        "sailing",
        "ski jumper",
        "skier",
        "snowboard",
        "sporting",
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
        "filmographies",
        "season",
        "highway",
        "motorway",
        "county road",
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

    MONTHS_EN_PATTERN = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    if re.search(r"^" + MONTHS_EN_PATTERN + r" in ", c, re.IGNORECASE):
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


def bump_db_to_new_version(wiki_db_dir: Path, old_version: int, lang: str) -> Path:
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
    
    return dst_db_file




def update_is_target_candidate(wiki_db_dir: Path, old_version: int, lang: str):
    db_file = bump_db_to_new_version(wiki_db_dir, old_version, lang)
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
    parser.add_argument("old_version", type=int)
    args = parser.parse_args()

    lang = args.lang
    wiki_db_dir = MAIN_DIR / "data" / "db" / "wiki"
    update_is_target_candidate(wiki_db_dir, args.old_version, lang)

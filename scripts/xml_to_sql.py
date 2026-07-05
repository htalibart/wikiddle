from typing import Optional
from pathlib import Path
import re
import bz2
import xml.etree.ElementTree as ET
import duckdb
import csv
import time
import json
import argparse
import requests

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent

SCHEMA_VERSION = 4

LINK_RE = re.compile(r"\[\[([^|\]#]+)")
TEMPLATE_RE = re.compile(r'\{\{\s*([^|}]+?)\s*[|}]')

CATEGORY_PREFIX = {
    'en': 'Category',
    'fr': 'Catégorie',
}

MIN_PAGE_LENGTH = 200

STRIP_ALL_RE = re.compile(r'\{\{|\{\||\}\}|\|\}|\[\[|\]\]')
STRIP_REFS_RE = re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL)
STRIP_TAGS_RE = re.compile(r'<[^>]+>', re.DOTALL)
STRIP_HEADERS_RE = re.compile(r'={2,}[^=]*={2,}')
STRIP_LIST_ITEMS_RE = re.compile(r'^\*.*$', re.MULTILINE)


def strip_templates_tables_and_links(text: str) -> str:
    result = []
    depth = 0
    mode = None
    start = 0
    for m in STRIP_ALL_RE.finditer(text):
        token = m.group()
        if depth == 0:
            if token in ('{{', '{|', '[['):
                result.append(text[start:m.start()])
                mode = token
                depth = 1
        else:
            if token == '{{' and mode == '{{':
                depth += 1
            elif token == '}}' and mode == '{{':
                depth -= 1
                if depth == 0:
                    start = m.end()
                    mode = None
            elif token == '{|' and mode == '{|':
                depth += 1
            elif token == '|}' and mode == '{|':
                depth -= 1
                if depth == 0:
                    start = m.end()
                    mode = None
            elif token == '[[' and mode == '[[':
                depth += 1
            elif token == ']]' and mode == '[[':
                depth -= 1
                if depth == 0:
                    start = m.end()
                    mode = None
    result.append(text[start:])
    return ''.join(result)


def get_category_re(language: str) -> re.Pattern:
    prefix = CATEGORY_PREFIX.get(language, 'Category')
    return re.compile(r'\[\[' + re.escape(prefix) + r':([^\]|]+)', re.IGNORECASE)


def fetch_namespaces(language: str) -> set[str]:
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "meta": "siteinfo",
        "siprop": "namespaces",
        "format": "json",
    }
    res = requests.get(url, params=params, headers={"User-Agent": "wikiddle/1.0"})
    res.raise_for_status()
    data = res.json()
    namespaces = set()
    for ns in data["query"]["namespaces"].values():
        for key in ("*", "canonical"):
            name = ns.get(key, "").strip()
            if name:
                namespaces.add(name + ":")
    return namespaces

def fetch_page_content(language: str, title: str) -> str:
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
    }
    res = requests.get(url, params=params, headers={"User-Agent": "wikiddle/1.0"})
    res.raise_for_status()
    data = res.json()
    page = next(iter(data["query"]["pages"].values()))
    return page["revisions"][0]["*"]


def fetch_english_disambiguation_templates() -> set[str]:
    lua_code = fetch_page_content("en", "Module:Disambiguation/templates")
    templates = re.findall(r'\["([^"]+)"\]', lua_code)
    return {t.strip().lower() for t in templates}


def fetch_mediawiki_disambiguation_templates(language: str) -> set[str]:
    content = fetch_page_content(language, "MediaWiki:Disambiguationspage")
    templates = re.findall(r'\{\{(?:Template:)?([^}|]+)', content, re.IGNORECASE)
    return {t.strip().lower() for t in templates}


def fetch_disambiguation_templates(language: str) -> set[str]:
    if language == "en":
        return fetch_english_disambiguation_templates()
    return fetch_mediawiki_disambiguation_templates(language)

def load_or_fetch_json(path: Path, fetch_fn, *args) -> set[str]:
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    data = fetch_fn(*args)
    with open(path, "w") as f:
        json.dump(list(data), f)
    return data


def keep_title(title: str, namespaces: set[str]) -> bool:
    for ns in namespaces:
        if title.startswith(ns):
            return False
    return True


def is_disambig(text: str, disambig_templates: set[str]) -> bool:
    if "__DISAMBIG__" in text:
        return True
    for match in TEMPLATE_RE.finditer(text):
        if match.group(1).lower() in disambig_templates:
            return True
    return False


def keep_text(text: Optional[str], disambig_templates: set[str]) -> bool:
    if text is None:
        return False
    if is_disambig(text, disambig_templates):
        return False
    if len(text) <= MIN_PAGE_LENGTH:
        return False
    return True


def count_words(text: str) -> int:
    text = strip_templates_tables_and_links(text)
    text = STRIP_LIST_ITEMS_RE.sub('', text)
    text = STRIP_REFS_RE.sub('', text)
    text = STRIP_TAGS_RE.sub('', text)
    text = STRIP_HEADERS_RE.sub('', text)
    return sum(1 for w in text.split() if re.search(r'[a-zA-ZÀ-ÿ0-9]', w))


def iter_pages(xml_file: Path, namespaces: set[str], disambig_templates: set[str]):
    with bz2.open(xml_file, 'rb') as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if not elem.tag.endswith("page"):
                continue
            if elem.find("{*}redirect") is not None:
                elem.clear()
                continue
            title = elem.find("{*}title").text
            if not keep_title(title, namespaces):
                elem.clear()
                continue
            page_id = int(elem.find("./{*}id").text)
            text_elem = elem.find(".//{*}text")
            if text_elem is None:
                elem.clear()
                continue
            text = text_elem.text
            if not keep_text(text, disambig_templates):
                elem.clear()
                continue
            elem.clear()
            yield page_id, title, text


def read_nodes_edges_and_categories(xml_file: Path, articles_writer, links_writer, categories_writer, namespaces: set[str], disambig_templates: set[str], category_re: re.Pattern):
    start_time = time.time()
    for page_count, (page_id, title, text) in enumerate(iter_pages(xml_file, namespaces, disambig_templates)):
        links = set()
        for link in LINK_RE.findall(text):
            link = link.strip('\n\r')
            if not link:
                continue
            link = link[0].upper() + link[1:]
            if keep_title(link, namespaces):
                links.add(link)
        for link in links:
            links_writer.writerow((page_id, link))

        categories = set()
        for category in category_re.findall(text):
            category = category.strip()
            if category:
                categories.add(category)
        for category in categories:
            categories_writer.writerow((page_id, category))

        nb_words = count_words(text)

        articles_writer.writerow((page_id, title, len(text), len(links), nb_words))
        if page_count % 10_000 == 0 and page_count > 0:
            elapsed = time.time() - start_time
            print(f"{page_count} pages in {elapsed:.1f}s ({page_count/elapsed:.0f} pages/s)")


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("language", type=str, default='en')
    args = parser.parse_args()
    language = args.language

    category_re = get_category_re(language)

    data_dir = MAIN_DIR/"data"
    lang_data_dir = data_dir/"metadata"/language
    lang_data_dir.mkdir(parents=True, exist_ok=True)

    print("Loading namespaces...")
    namespaces = load_or_fetch_json(
        lang_data_dir/"namespaces.json",
        fetch_namespaces,
        language
    )

    print("Loading disambiguation templates...")
    disambig_templates = load_or_fetch_json(
        lang_data_dir/"disambiguation_templates.json",
        fetch_disambiguation_templates,
        language
    )

    xml_dir = data_dir/"xml"/language
    xml_files = sorted(xml_dir.glob(f'{language}wiki-*.xml*.bz2'))
    assert xml_files, "No XML files found in data_dir"

    db_dir = data_dir/"db"/"wiki"/f"v{SCHEMA_VERSION}"
    tmp_dir = data_dir/"tmp"/"wiki"/f"v{SCHEMA_VERSION}"/language
    db_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    db_file = db_dir/f"{language}.db"
    articles_file = tmp_dir/"articles.csv"
    links_file = tmp_dir/"links_raw.csv"
    categories_file = tmp_dir/"categories_raw.csv"

    with open(articles_file, 'w', newline='') as af, open(links_file, 'w', newline='') as lf, open(categories_file, 'w', newline='') as cf:
        articles_writer = csv.writer(af, delimiter='\t')
        links_writer = csv.writer(lf, delimiter='\t')
        categories_writer = csv.writer(cf, delimiter='\t')
        for xml_file in xml_files:
            print(f"Reading {xml_file.name}...")
            read_nodes_edges_and_categories(xml_file, articles_writer, links_writer, categories_writer, namespaces, disambig_templates, category_re)

    print("Loading into DuckDB...")
    con = duckdb.connect(str(db_file))
    con.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    con.execute("INSERT INTO metadata VALUES ('schema_version', ?)", [str(SCHEMA_VERSION)])
    con.execute("""
        CREATE TABLE articles (
            id BIGINT,
            title TEXT NOT NULL,
            article_length INTEGER,
            nb_links INTEGER,
            nb_words INTEGER,
            nb_backlinks INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE TABLE links_raw (
            source_id BIGINT,
            target_title TEXT
        )
    """)
    con.execute("""
        CREATE TABLE categories_raw (
            article_id BIGINT,
            category_name TEXT
        )
    """)
    con.execute(f"COPY articles(id, title, article_length, nb_links, nb_words) FROM '{articles_file}' (DELIMITER '\t')")
    con.execute(f"COPY links_raw FROM '{links_file}' (DELIMITER '\t', QUOTE '\"')")
    con.execute(f"COPY categories_raw FROM '{categories_file}' (DELIMITER '\t', QUOTE '\"')")

    print("Resolving link targets...")
    con.execute("""
        CREATE TABLE links AS
        SELECT l.source_id, a.id AS target_id
        FROM links_raw l
        JOIN articles a ON a.title = l.target_title
    """)
    con.execute("DROP TABLE links_raw")
    print("Done with link targets.")

    print("Computing backlink counts...")
    update_nb_backlinks(con)
    print("Done with backlink counts.")

    print("Resolving categories...")
    con.execute("""
        CREATE TABLE categories AS
        SELECT row_number() OVER (ORDER BY category_name) AS id, category_name AS name
        FROM (
            SELECT DISTINCT category_name
            FROM categories_raw
        )
    """)
    con.execute("""
        CREATE TABLE article_categories AS
        SELECT cr.article_id, c.id AS category_id
        FROM categories_raw cr
        JOIN categories c ON c.name = cr.category_name
    """)
    con.execute("DROP TABLE categories_raw")
    print("Done with categories.")

    con.execute("CREATE INDEX idx_source ON links(source_id)")
    con.execute("CREATE INDEX idx_target ON links(target_id)")
    con.execute("CREATE INDEX idx_category_name ON categories(name)")
    con.execute("CREATE INDEX idx_article_category_article ON article_categories(article_id)")
    con.execute("CREATE INDEX idx_article_category_category ON article_categories(category_id)")
    con.execute("CREATE INDEX idx_nb_backlinks ON articles(nb_backlinks)")
    con.close()
    print("Done.")

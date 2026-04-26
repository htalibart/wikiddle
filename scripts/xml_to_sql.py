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

LINK_RE = re.compile(r"\[\[([^|\]#]+)")
TEMPLATE_RE = re.compile(r'\{\{\s*([^|}]+?)\s*[|}]')

MIN_PAGE_LENGTH = 200


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

def fetch_disambiguation_templates(language: str) -> set[str]:
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": "MediaWiki:Disambiguationspage",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
    }
    res = requests.get(url, params=params, headers={"User-Agent": "wikiddle/1.0"})
    res.raise_for_status()
    data = res.json()
    page = next(iter(data["query"]["pages"].values()))
    content = page["revisions"][0]["*"]
    # extract template names from lines like "* {{Template:Homonymie}}"
    templates = re.findall(r'\{\{(?:Template:)?([^}|]+)', content, re.IGNORECASE)
    return {t.strip().lower() for t in templates}


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
    if 'talk:' in title.lower():
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


def read_nodes_and_edges(xml_file: Path, articles_writer, links_writer, namespaces: set[str], disambig_templates: set[str]):
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
        articles_writer.writerow((page_id, title, len(text), len(links)))
        if page_count % 10_000 == 0 and page_count > 0:
            elapsed = time.time() - start_time
            print(f"{page_count} pages in {elapsed:.1f}s ({page_count/elapsed:.0f} pages/s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("language", type=str, default='en')
    args = parser.parse_args()
    language = args.language

    data_dir = MAIN_DIR / 'data'
    lang_data_dir = data_dir / language
    lang_data_dir.mkdir(parents=True, exist_ok=True)

    print("Loading namespaces...")
    namespaces = load_or_fetch_json(
        lang_data_dir / 'namespaces.json',
        fetch_namespaces,
        language
    )

    print("Loading disambiguation templates...")
    disambig_templates = load_or_fetch_json(
        lang_data_dir / 'disambiguation_templates.json',
        fetch_disambiguation_templates,
        language
    )

    xml_dir = data_dir / 'xml' / language
    xml_files = sorted(xml_dir.glob(f'{language}wiki-*.xml*.bz2'))
    assert xml_files, "No XML files found in data_dir"

    output_dir = data_dir / 'db' / language
    output_dir.mkdir(parents=True, exist_ok=True)
    db_file = output_dir / 'wiki.db'
    articles_file = output_dir / 'articles.csv'
    links_file = output_dir / 'links_raw.csv'

    with open(articles_file, 'w', newline='') as af, open(links_file, 'w', newline='') as lf:
        articles_writer = csv.writer(af, delimiter='\t')
        links_writer = csv.writer(lf, delimiter='\t')
        for xml_file in xml_files:
            print(f"Reading {xml_file.name}...")
            read_nodes_and_edges(xml_file, articles_writer, links_writer, namespaces, disambig_templates)

    print("Loading into DuckDB...")
    con = duckdb.connect(str(db_file))
    con.execute("""
        CREATE TABLE articles (
            id BIGINT,
            title TEXT NOT NULL,
            article_length INTEGER,
            nb_links INTEGER,
        )
    """)
    con.execute("""
        CREATE TABLE links_raw (
            source_id BIGINT,
            target_title TEXT
        )
    """)
    con.execute(f"COPY articles FROM '{articles_file}' (DELIMITER '\t')")
    con.execute(f"COPY links_raw FROM '{links_file}' (DELIMITER '\t', QUOTE '\"')")

    print("Resolving link targets...")
    con.execute("""
        CREATE TABLE links AS
        SELECT l.source_id, a.id AS target_id
        FROM links_raw l
        JOIN articles a ON a.title = l.target_title
    """)
    con.execute("DROP TABLE links_raw")
    print("Done with link targets.")

    con.execute("CREATE INDEX idx_source ON links(source_id)")
    con.execute("CREATE INDEX idx_target ON links(target_id)")
    con.close()
    print("Done.")
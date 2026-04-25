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

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent

LINK_RE = re.compile(r"\[\[([^|\]#]+)")
TEMPLATE_RE = re.compile(r'\{\{\s*([^|}]+?)\s*[|}]')

# from https://en.wikipedia.org/wiki/Wikipedia:Namespace
TITLE_FILTERS = (
    'Book:',
    'Category:',
    'Draft:',
    'Education Program:',
    'Event:',
    'File:',
    'Gadget:',
    'Gadget definition:',
    'Help:',
    'Index of',
    'List of',
    'Media:',
    'MediaWiki:',
    'Module:',
    'MOS:',
    'Portal:',
    'Special:',
    'Talk:',
    'Template:',
    'TimedText:',
    'Topic:',
    'User:',
    'Wikipedia:',
)

MIN_PAGE_LENGTH = 200

with open(MAIN_DIR / 'data' / 'disambiguation_templates.json') as f:
    DISAMBIG_TEMPLATES = set(json.load(f))

def keep_title(title: str) -> bool:
    if title.startswith(TITLE_FILTERS):
        return False
    if 'talk:' in title.lower():
        return False
    return True

def is_disambig(text: str) -> bool:
    if "__DISAMBIG__" in text:
        return True
    for match in TEMPLATE_RE.finditer(text):
        if match.group(1).lower() in DISAMBIG_TEMPLATES:
            return True
    return False

def keep_text(text: Optional[str]) -> bool:
    if text is None:
        return False
    if is_disambig(text):
        return False
    if len(text) <= MIN_PAGE_LENGTH:
        return False
    return True

def iter_pages(xml_file: Path):
    with bz2.open(xml_file, 'rb') as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if not elem.tag.endswith("page"):
                continue
            if elem.find("{*}redirect") is not None:
                elem.clear()
                continue
            title = elem.find("{*}title").text
            if not keep_title(title):
                elem.clear()
                continue
            page_id = int(elem.find("./{*}id").text)
            text_elem = elem.find(".//{*}text")
            if text_elem is None:
                elem.clear()
                continue
            text = text_elem.text
            if not keep_text(text):
                elem.clear()
                continue
            elem.clear()
            yield page_id, title, text

def read_nodes_and_edges(xml_file: Path, articles_writer, links_writer):
    start_time = time.time()
    for page_count, (page_id, title, text) in enumerate(iter_pages(xml_file)):

        links = set()
        for link in LINK_RE.findall(text):
            link = link.strip('\n\r')
            if not link:
                continue
            link = link[0].upper() + link[1:]
            if keep_title(link):
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
            read_nodes_and_edges(xml_file, articles_writer, links_writer)

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
    con.execute(f"COPY links_raw FROM '{links_file}' (DELIMITER '\t')")

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

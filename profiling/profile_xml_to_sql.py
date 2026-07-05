import cProfile
import pstats
import sys
import csv
import io
from pathlib import Path

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent
sys.path.insert(0, str(MAIN_DIR / "scripts"))

from xml_to_sql import read_nodes_edges_and_categories, get_category_re, load_or_fetch_json, fetch_namespaces, fetch_disambiguation_templates


if __name__=="__main__":

    language = "en"
    data_dir = MAIN_DIR / "data"
    lang_data_dir = data_dir / "metadata" / language

    namespaces = load_or_fetch_json(lang_data_dir / "namespaces.json", fetch_namespaces, language)
    disambig_templates = load_or_fetch_json(lang_data_dir / "disambiguation_templates.json", fetch_disambiguation_templates, language)
    category_re = get_category_re(language)

    xml_dir = data_dir / "xml" / language
    xml_file = sorted(xml_dir.glob(f'{language}wiki-*.xml*.bz2'), key=lambda f: f.stat().st_size)[0]

    articles_writer = csv.writer(io.StringIO(), delimiter='\t')
    links_writer = csv.writer(io.StringIO(), delimiter='\t')
    categories_writer = csv.writer(io.StringIO(), delimiter='\t')

    def run_subset():
        read_nodes_edges_and_categories(xml_file, articles_writer, links_writer, categories_writer, namespaces, disambig_templates, category_re)

    output_dir = THIS_DIR / "profiling_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "profile_xml_to_sql.out"

    cProfile.run("run_subset()", str(output_file))

    p = pstats.Stats(str(output_file))
    p.sort_stats("cumulative").print_stats(15)

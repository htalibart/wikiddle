# cf https://en.wikipedia.org/wiki/Module:Disambiguation/templates and https://en.wikipedia.org/wiki/Module:Disambiguation

import re
import requests
import json
from pathlib import Path

THIS_DIR = Path(__file__).parent
MAIN_DIR = THIS_DIR.parent

if __name__ == "__main__":
    response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": "Module:Disambiguation/templates",
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
        },
        headers={
            "User-Agent": "wikiddle/1.0"
        }
    )

    data = response.json()
    page = next(iter(data["query"]["pages"].values()))
    lua_code = page["revisions"][0]["*"]
    templates = [t.lower() for t in re.findall(r'\["([^"]+)"\]', lua_code)]

    data_dir = MAIN_DIR / 'data'
    with open(data_dir / 'disambiguation_templates.json', 'w') as jf:
        json.dump(templates, jf)

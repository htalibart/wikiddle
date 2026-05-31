import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, _cached_daily_targets, open_wiki_db_con, get_schema_version, get_daily_article_filter

DATA_DIR = Path(__file__).parent.parent.parent/"data"

os.environ.setdefault("WIKI_DB_DIR", str(DATA_DIR/"db"/"wiki"))
os.environ.setdefault("WIKI_VERSION", "2")
os.environ.setdefault("GAMES_DB", str(DATA_DIR/"db"/"games"/"v1.db"))

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def reset_cache():
    for lang in _cached_daily_targets:
        _cached_daily_targets[lang].update({"id": None, "title": None, "date": None})


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("lang", ["en", "fr"])
class TestDailyArticle:
    def test_returns_id_and_title(self, client, lang):
        res = client.get(f"/api/{lang}/daily-article")
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert "title" in data


@pytest.mark.parametrize("lang", ["en", "fr"])
class TestArticle:
    def test_known_id(self, client, lang):
        daily = client.get(f"/api/{lang}/daily-article").json()
        res = client.get(f"/api/{lang}/article-title?id={daily['id']}")
        assert res.status_code == 200
        assert res.json()["title"] == daily["title"]

    def test_known_title(self, client, lang):
        daily = client.get(f"/api/{lang}/daily-article").json()
        res = client.get(f"/api/{lang}/article-id?title={daily['title']}")
        assert res.status_code == 200
        assert res.json()["id"] == daily["id"]


@pytest.mark.parametrize("lang,query", [("en", "python"), ("fr", "python")])
class TestSearchArticles:
    def test_returns_results(self, client, lang, query):
        res = client.get(f"/api/{lang}/articles?query={query}")
        assert res.status_code == 200

    def test_no_results(self, client, lang, query):
        res = client.get(f"/api/{lang}/articles?query=bliblablouIdontexisthihihi")
        assert res.status_code == 200
        assert res.json() == []

    def test_max_results(self, client, lang, query):
        res = client.get(f"/api/{lang}/articles?query=a")
        assert res.status_code == 200
        assert len(res.json()) == 30

    def test_exact_match_comes_first(self, client, lang, query):
        daily_title = client.get(f"/api/{lang}/daily-article").json()["title"]
        res = client.get(f"/api/{lang}/articles?query={daily_title}")
        assert res.status_code == 200
        assert res.json()[0]["title"] == daily_title


@pytest.mark.parametrize("lang", ["en", "fr"])
class TestCommonNeighbors:
    def test_correct_guess(self, client, lang):
        daily_id = client.get(f"/api/{lang}/daily-article").json()["id"]
        res = client.get(f"/api/{lang}/common-links?id={daily_id}")
        assert res.status_code == 200
        assert res.json()["is_target"] is True

    def test_other_guess(self, client, lang):
        res = client.get(f"/api/{lang}/common-links?id=12")
        assert res.status_code == 200
        data = res.json()
        assert "is_target" in data
        assert "common" in data


class TestArticleFilters:

    def can_be_daily_target(self, lang: str, title: str):
        con = open_wiki_db_con(lang)
        try:
            schema_version = get_schema_version(con)
            article_filter = get_daily_article_filter(schema_version)
            row = con.execute(
                f"""
                SELECT id
                FROM articles
                WHERE title = ?
                AND {article_filter}
                """,
                [title]
            ).fetchone()
        finally:
            con.close()

        return row is not None


    @pytest.mark.parametrize("lang,title", [
        ("fr", "Bruxelles"),
        ("en", "Brussels"),
        ("fr", "Paris"),
        ("en", "Paris"),
        ("fr", "Marseille"),
        ("en", "Marseille"),
        ("fr", "Londres"),
        ("en", "London"),
        ("fr", "Liverpool"),
        ("en", "Liverpool"),
        ("fr", "Belgique"),
        ("en", "Belgium"),
        ("fr", "France"),
        ("en", "France"),
        ("fr", "Anvers"),
        ("en", "Antwerp"),
        ("fr", "Cinéma"),
        ])
    def test_article_can_be_daily_target(self, lang: str, title: str):
        assert self.can_be_daily_target(lang, title)


    @pytest.mark.parametrize("lang,title", [
        ("en", "2022–23 Bangladesh Premier League (football)"),
        ("fr", "Suture lacrymo-maxillaire"),
        ("fr", "Jay Christianson"),
        ("fr", "Slalom géant parallèle féminin de snowboard aux Jeux olympiques de 2022"),
        ("fr", "14ymedio"),
        ("fr", "Église Saint-Pierre d'Anères"),
        ])
    def test_article_cant_be_daily_target(self, lang: str, title: str):
        assert not self.can_be_daily_target(lang, title)

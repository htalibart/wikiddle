import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from main import _cached_daily_targets, app

DATA_DIR = Path(__file__).parent.parent / "data"

os.environ.setdefault("WIKI_DB_DIR", str(DATA_DIR / "db" / "wiki"))
os.environ.setdefault("WIKI_VERSION", "8")
os.environ.setdefault("GAMES_DB", str(DATA_DIR / "db" / "games" / "v2.db"))

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def reset_cache():
    for lang in _cached_daily_targets:
        _cached_daily_targets[lang].update({"id": None, "title": None, "date": None, "wiki_db_version": None})


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
        res = client.get(f"/api/{lang}/article-title", params={"id": daily["id"]})
        assert res.status_code == 200
        assert res.json()["title"] == daily["title"]

    def test_known_title(self, client, lang):
        daily = client.get(f"/api/{lang}/daily-article").json()
        res = client.get(f"/api/{lang}/article-id", params={"title": daily["title"]})
        assert res.status_code == 200
        assert res.json()["id"] == daily["id"]


@pytest.mark.parametrize("lang,query", [("en", "python"), ("fr", "python")])
class TestSearchArticles:
    def test_returns_results(self, client, lang, query):
        res = client.get(f"/api/{lang}/articles", params={"query": query})
        assert res.status_code == 200

    def test_no_results(self, client, lang, query):
        res = client.get(f"/api/{lang}/articles", params={"query": "bliblablouIdontexisthihihi"})
        assert res.status_code == 200
        assert res.json() == []

    def test_max_results(self, client, lang, query):
        res = client.get(f"/api/{lang}/articles", params={"query": "a"})
        assert res.status_code == 200
        assert len(res.json()) == 30

    def test_exact_match_comes_first(self, client, lang, query):
        title = "Brussels" if lang == "en" else "Bruxelles"
        res = client.get(f"/api/{lang}/articles", params={"query": title})
        assert res.status_code == 200
        assert res.json()[0]["title"] == title


@pytest.mark.parametrize("lang", ["en", "fr"])
class TestCommonInfo:
    def test_correct_guess(self, client, lang):
        daily_id = client.get(f"/api/{lang}/daily-article").json()["id"]
        res = client.get(f"/api/{lang}/common-info?id={daily_id}")
        assert res.status_code == 200
        assert res.json()["is_target"] is True

    def test_other_guess(self, client, lang):
        res = client.get(f"/api/{lang}/common-info?id=12")
        assert res.status_code == 200
        data = res.json()
        assert "is_target" in data
        assert "common_links" in data
        assert "common_categories" in data

    def test_daily_target_has_categories(self, client, lang):
        daily_id = client.get(f"/api/{lang}/daily-article").json()["id"]
        res = client.get(f"/api/{lang}/common-info?id={daily_id}")
        assert res.status_code == 200
        # the daily target should share categories with itself
        assert len(res.json()["common_categories"]) > 0

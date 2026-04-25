import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient

from main import app, _cached_daily_target

os.environ["WIKI_DB_PATH"] = str(Path(__file__).parent.parent.parent / "data" / "wiki.db")


@pytest.fixture(autouse=True)
def reset_cache():
    _cached_daily_target.update({"id": None, "title": None, "date": None})


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestDailyArticle:
    def test_returns_id_and_title(self, client):
        res = client.get("/api/daily-article")
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert "title" in data


class TestArticle:
    def test_known_id(self, client):
        daily = client.get("/api/daily-article").json()
        res = client.get(f"/api/article-title?id={daily['id']}")
        assert res.json()["title"] == daily["title"]

    def test_known_title(self, client):
        daily = client.get("/api/daily-article").json()
        res = client.get(f"/api/article-id?title={daily['title']}")
        assert res.status_code == 200
        assert res.json()["id"] == daily["id"]


class TestSearchArticles:
    def test_returns_results(self, client):
        res = client.get("/api/articles?query=python")
        assert res.status_code == 200

    def test_no_results(self, client):
        res = client.get("/api/articles?query=bliblablouIdontexisthihihi")
        assert res.json() == []

    def test_max_results(self, client):
        res = client.get("/api/articles?query=a")
        assert len(res.json()) == 30

    def test_exact_match_comes_first(self, client):
        daily_title = client.get("/api/daily-article").json()["title"]
        res = client.get(f"/api/articles?query={daily_title}")
        assert res.json()[0]["title"] == daily_title


class TestCommonNeighbors:
    def test_correct_guess(self, client):
        daily_id = client.get("/api/daily-article").json()["id"]
        res = client.get(f"/api/common-neighbors?id={daily_id}")
        assert res.status_code == 200
        assert res.json()["is_target"] is True

    def test_other_guess(self, client):
        res = client.get("/api/common-neighbors?id=12")
        assert res.status_code == 200
        data = res.json()
        assert "is_target" in data
        assert "common" in data

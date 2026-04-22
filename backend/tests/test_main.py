import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from datetime import date, timedelta

from main import app, get_daily_article_cached, _cached_daily_target, MIN_NB_LINKS


def make_con_mock(fetchone=None, fetchall=None):
    con = MagicMock()
    con.execute.return_value.fetchone.return_value = fetchone
    con.execute.return_value.fetchall.return_value = fetchall or []
    return con

def make_db_mock(article_id=42, title="Toto", count=1000):
    con = MagicMock()
    con.execute.return_value.fetchone.side_effect = [
        (count,),
        (article_id, title),
    ]
    return con


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c



class TestNotFound:
    def test_article_title_not_found(self, client):
        with patch("main.get_con", return_value=make_con_mock(fetchone=None)):
            res = client.get("/api/article-title?id=99999")
        assert res.status_code == 404

    def test_article_id_not_found(self, client):
        with patch("main.get_con", return_value=make_con_mock(fetchone=None)):
            res = client.get("/api/article-id?title=Toto")
        assert res.status_code == 404


class TestMissingParams:
    def test_articles_missing_query(self, client):
        res = client.get("/api/articles")
        assert res.status_code == 422

    def test_article_title_missing_id(self, client):
        res = client.get("/api/article-title")
        assert res.status_code == 422

    def test_article_id_missing_title(self, client):
        res = client.get("/api/article-id")
        assert res.status_code == 422

    def test_common_neighbors_missing_id(self, client):
        res = client.get("/api/common-neighbors")
        assert res.status_code == 422



class TestCommonNeighbors:
    def _patches(self, daily_id, daily_neighbors, guess_neighbors):
        article = {"id": daily_id, "title": "Toto", "date": date.today()}

        def neighbors_side_effect(article_id):
            return daily_neighbors if article_id == daily_id else guess_neighbors

        return (
            patch("main.get_daily_article_cached", return_value=article),
            patch("main.get_neighbors", side_effect=neighbors_side_effect),
            patch("main.get_article_title", side_effect=lambda req, i: {"id": i, "title": f"Article {i}"}),
        )

    def test_correct_guess(self, client):
        daily_patch, neighbors_patch, title_patch = self._patches(42, {1, 2, 3}, {1, 2, 3})
        with daily_patch, neighbors_patch, title_patch:
            res = client.get("/api/common-neighbors?id=42")
        assert res.status_code == 200
        assert res.json()["is_target"] is True

    def test_wrong_guess(self, client):
        daily_patch, neighbors_patch, title_patch = self._patches(42, {1, 2, 3}, {2, 3, 4})
        with daily_patch, neighbors_patch, title_patch:
            res = client.get("/api/common-neighbors?id=12")
        assert res.status_code == 200
        data = res.json()
        assert data["is_target"] is False
        assert len(data["common"]) == 2  # {2, 3}

    def test_no_common_neighbors(self, client):
        daily_patch, neighbors_patch, title_patch = self._patches(42, {1, 2}, {3, 4})
        with daily_patch, neighbors_patch, title_patch:
            res = client.get("/api/common-neighbors?id=200")
        assert res.status_code == 200
        assert res.json()["common"] == []


class TestDailyArticleCached:
    def setup_method(self):
        _cached_daily_target.update({"id": None, "title": None, "date": None})

    def test_uses_cache_on_second_call(self):
        con = make_db_mock()
        with patch("main.get_con", return_value=con):
            get_daily_article_cached()
            get_daily_article_cached()
        assert con.execute.call_count == 2

    def test_refreshes_cache_next_day(self):
        yesterday = date.today() - timedelta(days=1)
        _cached_daily_target.update({"id": 12, "title": "Titi", "date": yesterday})
        con = make_db_mock(title="Toto")
        with patch("main.get_con", return_value=con):
            result = get_daily_article_cached()
        assert result["date"] == date.today()
        assert result["title"] == "Toto"

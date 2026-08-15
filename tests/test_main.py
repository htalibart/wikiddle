import os
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import (
    _cached_daily_targets,
    _cached_yesterday_targets,
    app,
    get_daily_article_cached,
    get_yesterdays_article_cached,
)


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


def make_games_con_mock(article_id=12, title="Titi", wiki_db_version=2):
    con = MagicMock()
    con.execute.return_value.fetchone.return_value = (article_id, title, wiki_db_version)
    return con


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestNotFound:
    def test_article_title_not_found(self, client):
        with patch("main.get_article_titles", return_value=[]):
            res = client.get("/api/en/article-title?id=99999")
        assert res.status_code == 404

    def test_article_id_not_found(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock(fetchone=None)),
        ):
            res = client.get("/api/en/article-id?title=Toto")
        assert res.status_code == 404


class TestMissingParams:
    def test_articles_missing_query(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock()),
        ):
            res = client.get("/api/en/articles")
        assert res.status_code == 422

    def test_article_title_missing_id(self, client):
        res = client.get("/api/en/article-title")
        assert res.status_code == 422

    def test_article_id_missing_title(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock()),
        ):
            res = client.get("/api/en/article-id")
        assert res.status_code == 422

    def test_common_info_missing_id(self, client):
        res = client.get("/api/en/common-info")
        assert res.status_code == 422


class TestCommonInfo:
    def _patches(self, daily_id, daily_links, guess_links, daily_cats=None, guess_cats=None):
        article = {"id": daily_id, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_cats = daily_cats or {}
        guess_cats = guess_cats or {}

        def links_side_effect(lang, article_id):
            return daily_links if article_id == daily_id else guess_links

        def cats_side_effect(lang, article_id):
            return daily_cats if article_id == daily_id else guess_cats

        return (
            patch("main.get_daily_article_cached", return_value=article),
            patch("main.get_links", side_effect=links_side_effect),
            patch("main.get_categories", side_effect=cats_side_effect),
        )

    def test_correct_guess(self, client):
        daily_patch, links_patch, cats_patch = self._patches(42, {1: "A", 2: "B", 3: "C"}, {1: "A", 2: "B", 3: "C"})
        with daily_patch, links_patch, cats_patch:
            res = client.get("/api/en/common-info?id=42")
        assert res.status_code == 200
        assert res.json()["is_target"] is True

    def test_wrong_guess(self, client):
        daily_patch, links_patch, cats_patch = self._patches(42, {1: "A", 2: "B", 3: "C"}, {2: "B", 3: "C", 4: "D"})
        with daily_patch, links_patch, cats_patch:
            res = client.get("/api/en/common-info?id=12")
        assert res.status_code == 200
        data = res.json()
        assert data["is_target"] is False
        assert len(data["common_links"]) == 2

    def test_no_common_links(self, client):
        daily_patch, links_patch, cats_patch = self._patches(42, {1: "A", 2: "B"}, {3: "C", 4: "D"})
        with daily_patch, links_patch, cats_patch:
            res = client.get("/api/en/common-info?id=200")
        assert res.status_code == 200
        assert res.json()["common_links"] == []

    def test_common_categories(self, client):
        daily_patch, links_patch, cats_patch = self._patches(
            42,
            {},
            {},
            daily_cats={10: "History", 20: "Science"},
            guess_cats={20: "Science", 30: "Sports"},
        )
        with daily_patch, links_patch, cats_patch:
            res = client.get("/api/en/common-info?id=12")
        assert res.status_code == 200
        assert res.json()["common_categories"] == ["Science"]

    def test_no_common_categories(self, client):
        daily_patch, links_patch, cats_patch = self._patches(
            42,
            {},
            {},
            daily_cats={10: "History"},
            guess_cats={20: "Science"},
        )
        with daily_patch, links_patch, cats_patch:
            res = client.get("/api/en/common-info?id=12")
        assert res.status_code == 200
        assert res.json()["common_categories"] == []


class TestDailyArticleCached:
    def setup_method(self):
        for lang in _cached_daily_targets:
            _cached_daily_targets[lang].update({"id": None, "title": None, "date": None, "wiki_db_version": None})

    def test_uses_cache_on_second_call(self):
        con = make_db_mock()
        with (
            patch.dict(os.environ, {"WIKI_VERSION": "2"}),
            patch("main.open_wiki_db_con", return_value=con) as mock_open_wiki_db_con,
            patch("main.open_games_db_con", return_value=make_con_mock()),
            patch("main.get_schema_version", return_value=1),
        ):
            get_daily_article_cached("en")
            get_daily_article_cached("en")
        assert mock_open_wiki_db_con.call_count == 1

    def test_uses_v2_filter(self):
        con = make_db_mock()
        with (
            patch.dict(os.environ, {"WIKI_VERSION": "2"}),
            patch("main.open_wiki_db_con", return_value=con),
            patch("main.open_games_db_con", return_value=make_con_mock()),
            patch("main.get_schema_version", return_value=2),
        ):
            get_daily_article_cached("en")

        queries = [call.args[0] for call in con.execute.call_args_list]
        assert any("is_target_candidate IS TRUE" in query for query in queries)
        assert not any("nb_backlinks" in query for query in queries)

    def test_refreshes_cache_next_day(self):
        yesterday = date.today() - timedelta(days=1)
        _cached_daily_targets["en"].update({"id": 12, "title": "Titi", "date": yesterday, "wiki_db_version": 2})

        con = make_db_mock(title="Toto")
        with (
            patch.dict(os.environ, {"WIKI_VERSION": "2"}),
            patch("main.open_wiki_db_con", return_value=con),
            patch("main.open_games_db_con", return_value=make_con_mock()),
            patch("main.get_schema_version", return_value=1),
        ):
            result = get_daily_article_cached("en")

        assert result["date"] == date.today()
        assert result["title"] == "Toto"
        assert result["wiki_db_version"] == 2

    def test_separate_cache_per_language(self):
        con_en = make_db_mock(article_id=42, title="Toto")
        con_fr = make_db_mock(article_id=84, title="Bonjour")

        with (
            patch.dict(os.environ, {"WIKI_VERSION": "2"}),
            patch("main.open_wiki_db_con", side_effect=[con_en, con_fr]),
            patch("main.open_games_db_con", return_value=make_con_mock()),
            patch("main.get_schema_version", return_value=1),
        ):
            result_en = get_daily_article_cached("en")
            result_fr = get_daily_article_cached("fr")

        assert result_en["id"] == 42
        assert result_en["title"] == "Toto"
        assert result_en["wiki_db_version"] == 2
        assert result_fr["id"] == 84
        assert result_fr["title"] == "Bonjour"
        assert result_fr["wiki_db_version"] == 2

    def test_existing_daily_article_uses_games_db_version(self):
        with (
            patch(
                "main.open_games_db_con",
                return_value=make_games_con_mock(article_id=12, title="Titi", wiki_db_version=2),
            ),
            patch("main.open_wiki_db_con") as mock_open_wiki_db_con,
        ):
            result = get_daily_article_cached("en")

        assert result["id"] == 12
        assert result["title"] == "Titi"
        assert result["wiki_db_version"] == 2
        mock_open_wiki_db_con.assert_not_called()

    def test_new_daily_article_stores_current_wiki_db_version(self):
        con = make_db_mock(article_id=42, title="Toto")
        games_con = make_con_mock()

        with (
            patch.dict(os.environ, {"WIKI_VERSION": "3"}),
            patch("main.open_wiki_db_con", return_value=con),
            patch("main.open_games_db_con", return_value=games_con),
            patch("main.get_schema_version", return_value=3),
        ):
            result = get_daily_article_cached("en")

        assert result["id"] == 42
        assert result["title"] == "Toto"
        assert result["wiki_db_version"] == 3

        insert_calls = [
            call for call in games_con.execute.call_args_list if "INSERT OR IGNORE INTO daily_articles" in call.args[0]
        ]
        assert len(insert_calls) == 1
        assert insert_calls[0].args[1][-1] == 3


class TestInvalidLang:
    def test_article_id_invalid_lang(self, client):
        res = client.get("/api/xx/article-id?title=Toto")
        assert res.status_code == 400

    def test_article_title_invalid_lang(self, client):
        res = client.get("/api/xx/article-title?id=42")
        assert res.status_code == 400

    def test_common_info_invalid_lang(self, client):
        res = client.get("/api/xx/common-info?id=42")
        assert res.status_code == 400

    def test_articles_invalid_lang(self, client):
        res = client.get("/api/xx/articles?query=foo")
        assert res.status_code == 400


class TestQueryValidation:
    def test_articles_query_too_long(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock()),
        ):
            res = client.get(f"/api/en/articles?query={'a' * 301}")
        assert res.status_code == 422

    def test_articles_query_empty(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock()),
        ):
            res = client.get("/api/en/articles?query=")
        assert res.status_code == 422

    def test_article_id_title_too_long(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock()),
        ):
            res = client.get(f"/api/en/article-id?title={'a' * 301}")
        assert res.status_code == 422

    def test_article_id_title_empty(self, client):
        with (
            patch("main.get_wiki_db_version_of_target", return_value=2),
            patch("main.open_wiki_db_con", return_value=make_con_mock()),
        ):
            res = client.get("/api/en/article-id?title=")
        assert res.status_code == 422


class TestSearchArticles:
    def test_search_articles(self, client):
        con = make_con_mock(fetchall=[(42, "Toto")])
        with (
            patch("main.get_wiki_db_version_of_target", return_value=8),
            patch("main.open_wiki_db_con", return_value=con) as mock_open_wiki_db_con,
            patch("main.get_schema_version", return_value=8),
        ):
            res = client.get("/api/en/articles?query=To")

        assert res.status_code == 200
        assert res.json() == [{"id": 42, "title": "Toto"}]
        mock_open_wiki_db_con.assert_called_once_with("en", 8)
        query = con.execute.call_args[0][0]
        assert "nb_backlinks >= 30" in query


class TestNewTargetLink:
    def _patches(self, target, links, titles):
        return (
            patch("main.get_daily_article_cached", return_value=target),
            patch("main.get_links", return_value=links),
            patch("main.get_article_titles", return_value=titles),
        )

    def test_returns_hint(self, client):
        target = {"id": 42, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_patch, links_patch, titles_patch = self._patches(
            target, {1: "A", 2: "B", 3: "C"}, ["Article 1", "Article 2", "Article 3"]
        )
        with daily_patch, links_patch, titles_patch:
            res = client.post("/api/en/new-target-link", json=[])
        assert res.status_code == 200
        assert res.json()["title"] is not None

    def test_excludes_already_guessed(self, client):
        target = {"id": 42, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_patch, links_patch, titles_patch = self._patches(
            target, {1: "A", 2: "B", 3: "C"}, ["Article 1", "Article 2", "Article 3"]
        )
        with daily_patch, links_patch, titles_patch:
            res = client.post("/api/en/new-target-link", json=["Article 1", "Article 2", "Article 3"])
        assert res.status_code == 200
        assert res.json()["title"] is None

    def test_invalid_lang(self, client):
        res = client.post("/api/xx/new-target-link", json=[])
        assert res.status_code == 400

    def test_empty_body(self, client):
        target = {"id": 42, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_patch, links_patch, titles_patch = self._patches(
            target, {1: "A", 2: "B", 3: "C"}, ["Article 1", "Article 2", "Article 3"]
        )
        with daily_patch, links_patch, titles_patch:
            res = client.post("/api/en/new-target-link")
        assert res.status_code == 200


class TestNewTargetCategory:
    def _patches(self, target, categories):
        return (
            patch("main.get_daily_article_cached", return_value=target),
            patch("main.get_categories", return_value=categories),
        )

    def test_returns_hint(self, client):
        target = {"id": 42, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_patch, categories_patch = self._patches(target, {1: "Category 1", 2: "Category 2", 3: "Category 3"})
        with daily_patch, categories_patch:
            res = client.post("/api/en/new-target-category", json=[])
        assert res.status_code == 200
        assert res.json()["title"] is not None

    def test_excludes_already_guessed(self, client):
        target = {"id": 42, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_patch, categories_patch = self._patches(target, {1: "Category 1", 2: "Category 2", 3: "Category 3"})
        with daily_patch, categories_patch:
            res = client.post("/api/en/new-target-category", json=["Category 1", "Category 2", "Category 3"])
        assert res.status_code == 200
        assert res.json()["title"] is None

    def test_invalid_lang(self, client):
        res = client.post("/api/xx/new-target-category", json=[])
        assert res.status_code == 400

    def test_empty_body(self, client):
        target = {"id": 42, "title": "Toto", "date": date.today(), "wiki_db_version": 2}
        daily_patch, categories_patch = self._patches(target, {1: "Category 1", 2: "Category 2", 3: "Category 3"})
        with daily_patch, categories_patch:
            res = client.post("/api/en/new-target-category")
        assert res.status_code == 200


class TestYesterdaysArticle:
    def setup_method(self):
        for lang in _cached_yesterday_targets:
            _cached_yesterday_targets[lang].update({"id": None, "title": None, "date": None})

    def test_returns_yesterdays_article(self, client):
        with patch(
            "main.open_games_db_con", return_value=make_games_con_mock(article_id=12, title="Titi", wiki_db_version=2)
        ):
            res = client.get("/api/en/yesterdays-article")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == 12
        assert data["title"] == "Titi"

    def test_not_found(self, client):
        with patch("main.open_games_db_con", return_value=make_con_mock(fetchone=None)):
            res = client.get("/api/en/yesterdays-article")
        assert res.status_code == 404

    def test_invalid_lang(self, client):
        res = client.get("/api/xx/yesterdays-article")
        assert res.status_code == 400


class TestYesterdaysArticleCached:
    def setup_method(self):
        for lang in _cached_yesterday_targets:
            _cached_yesterday_targets[lang].update({"id": None, "title": None, "date": None})

    def test_uses_cache_on_second_call(self):
        con = make_games_con_mock()
        with patch("main.open_games_db_con", return_value=con) as mock_open:
            get_yesterdays_article_cached("en")
            get_yesterdays_article_cached("en")
        assert mock_open.call_count == 1

    def test_refreshes_cache_when_stale(self):
        two_days_ago = date.today() - timedelta(days=2)
        _cached_yesterday_targets["en"].update({"id": 99, "title": "Toutou", "date": two_days_ago})

        con = make_games_con_mock(article_id=12, title="Titi", wiki_db_version=2)
        with patch("main.open_games_db_con", return_value=con):
            result = get_yesterdays_article_cached("en")

        yesterday = date.today() - timedelta(days=1)
        assert result["date"] == yesterday
        assert result["title"] == "Titi"

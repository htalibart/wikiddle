import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, _cached_daily_targets, open_wiki_db_con, get_schema_version, get_daily_article_filter

DATA_DIR = Path(__file__).parent.parent / "data"

os.environ.setdefault("WIKI_DB_DIR", str(DATA_DIR / "db" / "wiki"))
os.environ.setdefault("WIKI_VERSION", "4")
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


class TestArticleFilters:
    def can_be_daily_target(self, lang: str, title: str):
        wiki_db_version = int(os.environ["WIKI_VERSION"])
        con = open_wiki_db_con(lang, wiki_db_version)
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
                [title],
            ).fetchone()
        finally:
            con.close()

        return row is not None

    @pytest.mark.parametrize(
        "lang,title",
        [
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
            ("en", "Breaking Bad"),
            ("fr", "Breaking Bad"),
            ("en", "Dire Straits"),
            ("fr", "Dire Straits"),
            ("fr", "Peter Jackson"),
            ("en", "Peter Jackson"),
            ("fr", "Marie Curie"),
            ("en", "Marie Curie"),
            ("fr", "Le Parrain (film)"),
            ("en", "The Godfather"),
        ],
    )
    def test_article_can_be_daily_target(self, lang: str, title: str):
        assert self.can_be_daily_target(lang, title)

    @pytest.mark.parametrize(
        "lang,title",
        [
            ("en", "2022–23 Bangladesh Premier League (football)"),
            ("fr", "Suture lacrymo-maxillaire"),
            ("fr", "Jay Christianson"),
            ("fr", "Slalom géant parallèle féminin de snowboard aux Jeux olympiques de 2022"),
            ("fr", "14ymedio"),
            ("fr", "Église Saint-Pierre d'Anères"),
            ("en", "2022 Stockholm Open – Singles"),
            ("fr", "Liste des monuments historiques de la Haute-Corse"),
            ("fr", "Discographie de M. Pokora"),
            ("fr", "Noël mortel"),
            ("en", "Simpsons Roasting on an Open Fire"),
            ("fr", "2024 en musique"),
            ("fr", "Filmographie d'Alain Delon"),
            ("fr", "Gare de Saint-Germain-des-Fossés"),
            ("fr", "Autoroute A6"),
            ("en", "County Road 595 (Marquette County, Michigan)"),
            ("fr", "Station Bois-Franc"),
            ("fr", "Billboard Music Awards 2011"),
            ("fr", "13e arrondissement de Paris"),
            ("en", "Canton of Neuchâtel"),
            ("fr", "Rue Mouffetard"),
            ("fr", "Vallée de la Woluwe"),
            ("fr", "2017 à la télévision"),
            ("fr", "Conseil général de Seine-et-Oise"),
            ("fr", "6 novembre en sport"),
            ("en", "Pro Bowl"),
            ("fr", "Tour d'Espagne 2009"),
            ("fr", "Élections générales québécoises de 2018"),
            ("fr", "Arrondissement du duché de Lauenbourg"),
            ("en", "District of Duchy of Lauenburg"),
            ("fr", "Arte France Cinéma"),
            ("fr", "Finales du BWF World Tour"),
            ("fr", "Festival international du film documentaire d'Amsterdam"),
            ("fr", "L'Étrange Festival"),
            ("fr", "Crise de 2024 au parti Les Républicains"),
            ("fr", "Subdivisions du Togo"),
            ("fr", "Thamnophilidae"),
            ("fr", "Réseau de bus Massy-Juvisy"),
            ("fr", "1982 aux échecs"),
            ("fr", "Ligne de Lyon-Perrache à Genève (frontière)"),
            ("fr", "Non-inscrit au Parlement européen"),
            ("en", "Non-attached members"),
            ("fr", "FK Irtych Pavlodar"),
            ("fr", "52e cérémonie des Saturn Awards"),
            ("fr", "21 février aux Jeux olympiques d'hiver de 2026"),
            ("fr", "Canton de Rennes-Sud-Ouest"),
            ("fr", "Fiat CR.32"),
            ("en", "Fiat CR.32"),
            ("fr", "Agence de l'eau Adour-Garonne"),
            ("fr", "Palmarès du double messieurs des Internationaux de France"),
            ("fr", "3e division (France)"),
            ("en", "3rd Armored Division (France)"),
            ("fr", "Base aérienne 113 Saint-Dizier-Robinson"),
            ("fr", "Slalom géant masculin de ski alpin aux Jeux olympiques de 2026"),
            ("fr", "7e division d'infanterie (France)"),
            ("fr", "32e cérémonie des Oscars"),
            ("fr", "13 janvier"),
            ("en", "January 13"),
            ("fr", "27 décembre"),
            ("fr", "1er décembre"),
            ("fr", "Sikorsky S-92"),
            ("en", "2023 Northern Ireland Open"),

        ],
    )
    def test_article_cant_be_daily_target(self, lang: str, title: str):
        assert not self.can_be_daily_target(lang, title)

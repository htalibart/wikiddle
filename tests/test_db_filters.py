import os

import pytest
from main import get_daily_article_filter, get_schema_version, open_wiki_db_con


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
            ("fr", "Mars 2025"),
            ("fr", "27 décembre"),
            ("fr", "1er décembre"),
            ("fr", "Sikorsky S-92"),
            ("en", "2023 Northern Ireland Open"),
            ("fr", "Équitation aux Jeux olympiques d'été de 2004"),
            ("fr", "Prix littéraires 2010"),
            ("fr", "39e législature du Canada"),
            ("fr", "Suisse aux Jeux olympiques d'hiver de 2014"),
            ("fr", "Canon de 20 mm Oerlikon"),
            ("en", "Oerlikon 20 mm cannon"),
            ("fr", "U.S. Route 60"),
            ("fr", "TER Provence-Alpes-Côte d'Azur"),
            ("fr", "Primetime Emmy Award du meilleur acteur dans une série télévisée dramatique"),
            ("fr", "Browning BAR M1918"),
            ("fr", "43e division d'infanterie (France)"),
            ("fr", "Jeux olympiques d'hiver de 2018"),
            ("en", "2018 Winter Olympics"),
            ("fr", "Équipe des États-Unis de soccer"),
            ("fr", "Ligne H du Transilien"),
            ("fr", "Festival international du film de comédie de Liège"),
            ("fr", "Archives départementales des Hauts-de-Seine"),
            ("en", "2016 Croatian parliamentary election"),
            ("en", "AR-15–style rifle"),
            ("en", "2023 French Open – Men's singles qualifying"),
            ("en", "2017 French Socialist Party presidential primary"),
            ("fr", "Primaire citoyenne de 2017"),
            ("fr", "Lignes de bus Tisséo de 13 à 87"),
            ("en", "Club Atlético Independiente"),
            ("fr", "Club Atlético Independiente"),
            ("fr", "École nationale supérieure des mines de Paris"),
            ("fr", "Halftracks américains de la Seconde Guerre mondiale"),
            ("fr", "Université Bordeaux Montaigne"),
            ("fr", "Communauté d'agglomération du Pays Basque"),
            ("fr", "EDHEC Business School"),
            ("fr", "École nationale d'ingénieurs de Tarbes"),
            ("en", "131st Infantry Brigade (United Kingdom)"),
            ("en", "Sports in Canada"),
            ("en", "High-speed rail in Spain"),
            ("en", "MAS (motorboat)"),
            ("en", "North Carolina's 9th congressional district"),
            ("en", "Figure skating at the 2026 Winter Olympics – Ice dance"),
            ("en", "No. 23 Squadron RAF"),
            ("en", "University of California, Los Angeles"),
            ("en", "Department of the Prime Minister and Cabinet (Australia)"),
            ("en", "MTA Regional Bus Operations"),
            ("en", "Milwaukee Police Department"),
            ("en", "6th Rajputana Rifles"),
            ("en", "4th Infantry Regiment (United States)"),
            ("en", "Special administrative regions of China"),
            ("en", "Vehicle registration plates of Ohio"),
            ("en", "1926 United States House of Representatives elections"),
            ("en", "Citroën Xsara"),
            ("en", "Renault Zoe"),
            ("en", "Stanford University School of Engineering"),
            ("en", "University of Duisburg-Essen"),
            ("en", "Dartmouth–Hitchcock Medical Center"),
            ("en", "2016 Western & Southern Open – Women's singles"),
            ("en", "Rail transport in New South Wales"),
            ("en", "International Transport Workers' Federation"),
            ("en", "University Ranking by Academic Performance"),
            ("en", "LaGuardia Community College"),
            ("en", "90th Light Infantry Division (Wehrmacht)"),
            ("en", "2020 United States presidential election in New York"),
            ("en", "2017 Western & Southern Open – Men's singles"),
            ("en", "Cirencester (UK Parliament constituency)"),
        ],
    )
    def test_article_cant_be_daily_target(self, lang: str, title: str):
        assert not self.can_be_daily_target(lang, title)

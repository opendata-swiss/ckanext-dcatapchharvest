# -*- coding: utf-8 -*-

import json

import nose
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.dcat_helpers import get_langs
from ckanext.dcatapchharvest.profiles import DCAT, DCT
from ckanext.dcatapchharvest.tests.base_test_classes import BaseParseTest

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class TestSwissDCATAPProfileParsing(BaseParseTest):
    languages = get_langs()

    def test_rights_license(self):

        contents = self._get_file_contents("dataset-rights.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)

        datasets = [d for d in p.datasets()]

        # Dataset
        eq_(len(datasets), 1)
        dataset = datasets[0]

        # Resources
        eq_(len(dataset["resources"]), 1)
        resource = dataset["resources"][0]
        eq_(str(resource["rights"]), "https://opendata.swiss/terms-of-use#terms_by")
        eq_(
            str(resource["license"]), "https://opendata.swiss/terms-of-use#terms_by_ask"
        )

    def test_dataset_all_fields(self):

        contents = self._get_file_contents("1901.xml")

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        eq_(len(datasets), 1)

        dataset = datasets[0]
        extras = self._extras(dataset)

        # Basic fields
        assert all(
            l in dataset["title"] for l in self.languages
        ), "title contains all languages"
        eq_(dataset["title"]["de"], "Statistisches Jahrbuch der Schweiz 1901")
        eq_(dataset["title"]["fr"], "Annuaire statistique de la Suisse 1901")

        assert all(
            l in dataset["description"] for l in self.languages
        ), "description contains all languages"
        eq_(dataset["description"]["de"], "")
        eq_(dataset["url"], "https://www.bfs.admin.ch/bfs/de/home/statistiken.html")

        # Keywords
        assert all(
            l in dataset["keywords"] for l in self.languages
        ), "keywords contains all languages"
        eq_(
            sorted(dataset["keywords"]["de"]),
            ["publikation", "statistische-grundlagen-und-ubersichten"],
        )
        eq_(
            sorted(dataset["keywords"]["fr"]),
            ["bases-statistiques-et-generalites", "publication"],
        )
        eq_(
            sorted(dataset["keywords"]["it"]),
            ["basi-statistiche-e-presentazioni-generali", "pubblicazione"],
        )
        eq_(
            sorted(dataset["keywords"]["en"]),
            ["publication", "statistical-basis-and-overviews"],
        )
        eq_(
            sorted(dataset["tags"], key=lambda k: k["name"]),
            [
                {"name": "basas-statisticas-e-survistas"},
                {"name": "bases-statistiques-et-generalites"},
                {"name": "basi-statistiche-e-presentazioni-generali"},
                {"name": "pubblicazione"},
                {"name": "publication"},
                {"name": "publication"},
                {"name": "publikation"},
                {"name": "statistical-basis-and-overviews"},
                {"name": "statistische-grundlagen-und-ubersichten"},
            ],
        )

        #  Simple values
        eq_(dataset["issued"], "1900-12-31T00:00:00")
        eq_(dataset["modified"], "2018-04-24T19:30:57.197374")
        eq_(dataset["identifier"], "346266@bundesamt-fur-statistik-bfs")
        eq_(dataset["spatial"], "Schweiz")

        # Temporals
        temporal = dataset["temporals"][0]
        eq_(temporal["end_date"], "1901-12-31T00:00:00")

        eq_(temporal["start_date"], "1901-01-01T00:00:00")

        # Publisher
        publisher = json.loads(dataset["publisher"])
        eq_(publisher["name"], "Landesamt Topographie Swisstopo")
        eq_(publisher["url"], "https://swisstopo")

        # Contact points
        contact_point = dataset["contact_points"][0]
        eq_(contact_point["name"], "info@bfs.admin.ch")
        eq_(contact_point["email"], "auskunftsdienst@bfs.admin.ch")

        # See alsos
        see_also = dataset["see_alsos"][0]
        eq_(see_also["dataset_identifier"], "4682791@bundesamt-fur-statistik-bfs")

        relations = sorted(dataset["relations"], key=lambda relation: relation["url"])

        # Relations - only one label given, no language specified
        eq_(
            relations[0]["url"],
            "https://www.admin.ch/opc/de/classified-compilation/19920252/index.html",
        )
        for lang in self.languages:
            eq_(relations[0]["label"][lang], "legal_basis")

        # Relations - multilingual labels
        eq_(relations[1]["url"], "https://www.example.org/aaa")
        for lang in self.languages:
            eq_(relations[1]["label"][lang], "Text for label " + lang.upper())

        # Relations - no label given
        eq_(relations[2]["url"], "https://www.example.org/bbb")
        for lang in self.languages:
            eq_(relations[2]["label"][lang], "https://www.example.org/bbb")

        # Relations - label given, language specified but not German.
        # If there is no label given in a language, we try to get one from
        # another language, in the priority order 'en' -> 'de' -> 'fr' -> 'it'.
        # Here we test that we end up with a label text in all languages, even
        # though the source only had a label in Italian.
        eq_(relations[3]["url"], "https://www.example.org/ccc")
        for lang in self.languages:
            eq_(relations[3]["label"][lang], "Text for label IT")

        # Qualified relations
        qualified_relations = sorted(dataset["qualified_relations"])
        eq_(
            qualified_relations[0],
            {
                "relation": "http://example.org/Original987",
                "had_role": "http://www.iana.org/assignments/relation/original",
            },
        )
        eq_(
            qualified_relations[1],
            {
                "relation": "http://example.org/Related486",
                "had_role": "http://www.iana.org/assignments/relation/related",
            },
        )

        #  Lists
        eq_(sorted(dataset["language"]), ["de", "fr"])
        eq_(sorted(dataset["groups"]), [{"name": "gove"}])
        eq_(
            sorted(dataset["documentation"]),
            [
                "https://example.com/documentation-dataset-1",
                "https://example.com/documentation-dataset-2",
            ],
        )
        eq_(
            sorted(dataset["conforms_to"]),
            [
                "http://resource.geosciml.org/ontology/timescale/gts",
                "https://inspire.ec.europa.eu/documents",
            ],
        )

        # Dataset URI
        eq_(
            extras["uri"],
            "https://opendata.swiss/dataset/7451e012-64b2-4bbc-af20-a0e2bc61b585",
        )

        # Resources
        eq_(len(dataset["resources"]), 1)
        resource = dataset["resources"][0]

        #  Simple values
        assert all(
            l in resource["title"] for l in self.languages
        ), "resource title contains all languages"
        eq_(resource["title"]["fr"], "Annuaire statistique de la Suisse 1901")
        eq_(resource["title"]["de"], "")
        assert all(
            l in resource["description"] for l in self.languages
        ), "resource description contains all languages"
        eq_(resource["description"]["de"], "")
        eq_(resource["format"], "html")
        eq_(resource["media_type"], "text/html")
        eq_(resource["identifier"], "346265-fr@bundesamt-fur-statistik-bfs")
        eq_(resource["license"], "https://opendata.swiss/terms-of-use#terms_by")
        eq_(resource["rights"], "http://www.opendefinition.org/licenses/cc-zero")
        eq_(resource["language"], ["fr"])
        eq_(resource["issued"], "1900-12-31T00:00:00")
        eq_(resource["temporal_resolution"], "P1D")
        eq_(resource["url"], "https://www.bfs.admin.ch/asset/fr/hs-b-00.01-jb-1901")
        assert "download_url" not in resource, "download_url not available on resource"

        # Lists
        eq_(
            sorted(resource["documentation"]),
            [
                "https://example.com/documentation-distribution-1",
                "https://example.com/documentation-distribution-2",
            ],
        )
        eq_(
            sorted(resource["access_services"]),
            [
                "https://example.com/my-great-data-service-1",
                "https://geoportal.sachsen.de/md/685a4409-a026-430e-afad-1fa2881f9700",
            ],
        )

        # Distribution URI
        eq_(
            resource["uri"],
            "https://opendata.swiss/dataset/7451e012-64b2-4bbc-af20-a0e2bc61b585/resource/c8ec6ca0-6923-4cf3-92f2-95a10e6f8e25",
        )

    def test_dataset_issued_with_year_before_1900(self):

        contents = self._get_file_contents("1894.xml")

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        eq_(len(datasets), 1)

        dataset = datasets[0]

        # Check date values
        eq_(dataset["issued"], "1893-12-31T00:00:00")

        eq_(dataset["modified"], "2018-04-24T19:30:57.197374")

    def test_catalog(self):

        contents = self._get_file_contents("catalog.xml")

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        eq_(len(datasets), 2)

    def test_distribution_access_url(self):
        g = Graph()

        dataset1 = URIRef("http://example.org/datasets/1")
        g.add((dataset1, RDF.type, DCAT.Dataset))
        g.add((dataset1, DCT.identifier, Literal("1234@swisstopo")))

        distribution1_1 = URIRef("http://example.org/datasets/1/ds/1")
        g.add((distribution1_1, RDF.type, DCAT.Distribution))
        g.add((distribution1_1, DCAT.accessURL, Literal("http://access.url.org")))
        g.add((dataset1, DCAT.distribution, distribution1_1))

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.g = g

        datasets = [d for d in p.datasets()]

        resource = datasets[0]["resources"][0]

        eq_(resource["url"], "http://access.url.org")
        assert "download_url" not in resource

    def test_distribution_download_url(self):
        g = Graph()

        dataset1 = URIRef("http://example.org/datasets/1")
        g.add((dataset1, RDF.type, DCAT.Dataset))
        g.add((dataset1, DCT.identifier, Literal("1234@swisstopo")))

        distribution1_1 = URIRef("http://example.org/datasets/1/ds/1")
        g.add((distribution1_1, RDF.type, DCAT.Distribution))
        g.add((distribution1_1, DCAT.downloadURL, Literal("http://download.url.org")))
        g.add((dataset1, DCAT.distribution, distribution1_1))

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.g = g

        datasets = [d for d in p.datasets()]

        resource = datasets[0]["resources"][0]

        eq_(resource["url"], "http://download.url.org")
        eq_(resource["download_url"], "http://download.url.org")

    def test_distribution_both_access_and_download_url(self):
        g = Graph()

        dataset1 = URIRef("http://example.org/datasets/1")
        g.add((dataset1, RDF.type, DCAT.Dataset))
        g.add((dataset1, DCT.identifier, Literal("1234@swisstopo")))

        distribution1_1 = URIRef("http://example.org/datasets/1/ds/1")
        g.add((distribution1_1, RDF.type, DCAT.Distribution))
        g.add((distribution1_1, DCAT.accessURL, Literal("http://access.url.org")))
        g.add((distribution1_1, DCAT.downloadURL, Literal("http://download.url.org")))
        g.add((dataset1, DCAT.distribution, distribution1_1))

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.g = g

        datasets = [d for d in p.datasets()]

        resource = datasets[0]["resources"][0]

        eq_(resource["url"], "http://access.url.org")
        eq_(resource["download_url"], "http://download.url.org")

    def test_distribution_format_format_only(self):
        g = Graph()

        dataset1 = URIRef("http://example.org/datasets/1")
        g.add((dataset1, RDF.type, DCAT.Dataset))
        g.add((dataset1, DCT.identifier, Literal("1234@swisstopo")))

        distribution1_1 = URIRef("http://example.org/datasets/1/ds/1")
        g.add((distribution1_1, RDF.type, DCAT.Distribution))
        g.add((distribution1_1, DCT["format"], Literal("CSV")))
        g.add((dataset1, DCAT.distribution, distribution1_1))

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.g = g

        datasets = [d for d in p.datasets()]

        resource = datasets[0]["resources"][0]

    def test_temporals_accepted_formats(self):
        contents = self._get_file_contents("dataset-datetimes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        eq_(len(dataset["temporals"]), 10)

        eq_(
            sorted(dataset["temporals"]),
            [
                {
                    "start_date": "1990-01-01T00:00:00",
                    "end_date": "1991-04-04T12:30:30",
                },
                {
                    "start_date": "1992-01-02T00:00:00",
                    "end_date": "1993-12-03T23:59:59.999999",
                },
                {
                    "start_date": "1994-01-01T00:00:00",
                    "end_date": "1995-04-04T12:30:30",
                },
                {
                    "start_date": "1996-01-02T00:00:00",
                    "end_date": "1997-12-03T23:59:59.999999",
                },
                {
                    "start_date": "1998-04-01T00:00:00",
                    "end_date": "1999-06-30T23:59:59.999999",
                },
                {
                    "start_date": "2000-01-01T00:00:00",
                    "end_date": "2001-12-31T23:59:59.999999",
                },
                {
                    "start_date": "2002-01-01T00:00:00",
                    "end_date": "2003-04-04T12:30:30",
                },
                {
                    "start_date": "2004-01-02T00:00:00",
                    "end_date": "2005-12-03T23:59:59.999999",
                },
                {
                    "start_date": "2006-04-01T00:00:00",
                    "end_date": "2007-06-30T23:59:59.999999",
                },
                {
                    "start_date": "2008-01-01T00:00:00",
                    "end_date": "2009-12-31T23:59:59.999999",
                },
            ],
        )

    def test_temporals_incorrect_formats(self):
        # See comments in dataset-datetimes-bad.xml for reasons why temporals
        # are mapped/not mapped.
        contents = self._get_file_contents("dataset-datetimes-bad.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        eq_(len(dataset["temporals"]), 5)

        eq_(
            sorted(dataset["temporals"]),
            [
                {
                    "start_date": "1998-04-01T00:00:00",
                    "end_date": "1999-01-01T23:59:59.999999",
                },
                {
                    "start_date": "2000-11-21T00:00:00",
                    "end_date": "2001-01-01T23:59:59.999999",
                },
                {
                    "start_date": "2002-01-01T00:00:00",
                    "end_date": "2003-01-31T23:59:59.999999",
                },
                {
                    "start_date": "2004-01-01T00:00:00",
                    "end_date": "2005-12-31T23:59:59.999999",
                },
                {
                    "start_date": "2006-01-01T00:00:00",
                    "end_date": "2007-01-31T23:59:59.999999",
                },
            ],
        )

    def test_resource_issued_modified_accepted_formats(self):
        contents = self._get_file_contents("dataset-datetimes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]

        issued_dates = [distribution["issued"] for distribution in dataset["resources"]]
        eq_(
            sorted(issued_dates),
            [
                "1990-01-01T00:00:00",
                "1992-01-02T00:00:00",
                "1994-04-01T00:00:00",
                "1996-01-01T00:00:00",
            ],
        )
        modified_dates = [
            distribution["modified"] for distribution in dataset["resources"]
        ]
        eq_(
            sorted(modified_dates),
            [
                "1991-04-04T12:30:30",
                "1993-12-03T00:00:00",
                "1995-06-01T00:00:00",
                "1997-01-01T00:00:00",
            ],
        )

    def test_dataset_issued_modified_accepted_formats(self):
        contents = self._get_file_contents("catalog-datetimes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        datasets = [d for d in p.datasets()]

        eq_(len(datasets), 4)
        issued_dates = [dataset["issued"] for dataset in datasets]
        eq_(
            sorted(issued_dates),
            [
                "1990-12-31T23:00:00+00:00",
                "1992-12-31T00:00:00",
                "1994-12-01T00:00:00",
                "1996-01-01T00:00:00",
            ],
        )
        modified_dates = [dataset["modified"] for dataset in datasets]
        eq_(
            sorted(modified_dates),
            [
                "1991-02-19T23:00:00+00:00",
                "1993-02-19T00:00:00",
                "1995-02-01T00:00:00",
                "1997-01-01T00:00:00",
            ],
        )

    def test_multiple_rights_statements(self):
        """Even if there are multiple dct:rights nodes on a distribution, only
        the DCAT-AP CH v1-compatible one should be mapped onto the resource.
        """
        contents = self._get_file_contents("dataset-multiple-rights.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        resource = dataset["resources"][0]

        eq_(str(resource["rights"]), "https://opendata.swiss/terms-of-use#terms_by_ask")

    def test_eu_themes_mapping(self):
        contents = self._get_file_contents("catalog-themes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)

        for dataset in p.datasets():
            eq_(
                sorted(dataset["groups"]),
                [
                    {"name": "econ"},
                    {"name": "gove"},
                    {"name": "soci"},
                ],
                "Groups not mapped correctly for dataset {}".format(
                    dataset["identifier"]
                ),
            )

    def test_format_media_type(self):
        """Test that format and media type are parsed both from URIs and from
        strings
        """
        contents = self._get_file_contents("dataset-media-types.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)

        dataset = [d for d in p.datasets()][0]
        results = [
            (resource.get("format"), resource.get("media_type"))
            for resource in dataset["resources"]
        ]
        eq_(
            sorted(results),
            [
                ("esri_ascii_grid", "text/plain"),
                ("grid_ascii", "text/plain"),
                ("html", "text/html"),
                ("json", "application/json"),
                ("text/calendar", "text/calendar"),
            ],
        )

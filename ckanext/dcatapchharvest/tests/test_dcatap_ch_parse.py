import json
from pprint import pprint

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.dcat_helpers import get_langs
from ckanext.dcatapchharvest.profiles import DCAT, DCT
from ckanext.dcatapchharvest.tests.base_test_classes import BaseParseTest


class TestSwissDCATAPProfileParsing(BaseParseTest):
    languages = get_langs()

    def test_rights_license(self):

        contents = self._get_file_contents("dataset-rights.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)

        datasets = [d for d in p.datasets()]

        # Dataset
        assert len(datasets) == 1
        dataset = datasets[0]

        # Resources
        assert len(dataset["resources"]) == 1
        resource = dataset["resources"][0]
        assert str(resource["rights"]) == "https://opendata.swiss/terms-of-use#terms_by"
        assert (
            str(resource["license"])
            == "https://opendata.swiss/terms-of-use#terms_by_ask"
        )

    def test_dataset_all_fields(self):
        contents = self._get_file_contents("1901.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)

        datasets = [d for d in p.datasets()]

        assert len(datasets) == 1

        dataset = datasets[0]
        extras = self._extras(dataset)

        # Basic fields
        assert all(
            l in dataset["title"] for l in self.languages
        ), "title contains all languages"
        assert dataset["title"]["de"] == "Statistisches Jahrbuch der Schweiz 1901"
        assert dataset["title"]["fr"] == "Annuaire statistique de la Suisse 1901"

        assert all(
            l in dataset["description"] for l in self.languages
        ), "description contains all languages"
        assert dataset["description"]["de"] == ""
        assert dataset["url"] == "https://www.bfs.admin.ch/bfs/de/home/statistiken.html"

        # Keywords
        assert all(
            l in dataset["keywords"] for l in self.languages
        ), "keywords contains all languages"
        assert sorted(dataset["keywords"]["de"]) == [
            "publikation",
            "statistische-grundlagen-und-ubersichten",
        ]
        assert sorted(dataset["keywords"]["fr"]) == [
            "bases-statistiques-et-generalites",
            "publication",
        ]
        assert sorted(dataset["keywords"]["it"]) == [
            "basi-statistiche-e-presentazioni-generali",
            "pubblicazione",
        ]
        assert sorted(dataset["keywords"]["en"]) == [
            "publication",
            "statistical-basis-and-overviews",
        ]
        assert sorted(dataset["tags"], key=lambda k: k["name"]) == [
            {"name": "basas-statisticas-e-survistas"},
            {"name": "bases-statistiques-et-generalites"},
            {"name": "basi-statistiche-e-presentazioni-generali"},
            {"name": "pubblicazione"},
            {"name": "publication"},
            {"name": "publication"},
            {"name": "publikation"},
            {"name": "statistical-basis-and-overviews"},
            {"name": "statistische-grundlagen-und-ubersichten"},
        ]

        #  Simple values
        assert dataset["issued"] == "1900-12-31T00:00:00"
        assert dataset["modified"] == "2018-04-24T19:30:57.197374"
        assert dataset["identifier"] == "346266@bundesamt-fur-statistik-bfs"
        assert dataset["spatial"] == "Schweiz"

        # Temporals
        temporal = dataset["temporals"][0]
        assert temporal["end_date"] == "1901-12-31T00:00:00"

        assert temporal["start_date"] == "1901-01-01T00:00:00"

        # Publisher
        publisher = json.loads(dataset["publisher"])
        assert publisher["name"] == "Landesamt Topographie Swisstopo"
        assert publisher["url"] == "https://swisstopo"

        # Contact points
        contact_point = dataset["contact_points"][0]
        assert contact_point["name"] == "info@bfs.admin.ch"
        assert contact_point["email"] == "auskunftsdienst@bfs.admin.ch"

        # See alsos
        see_also = dataset["see_alsos"][0]
        assert see_also["dataset_identifier"] == "4682791@bundesamt-fur-statistik-bfs"

        relations = sorted(dataset["relations"], key=lambda relation: relation["url"])

        # Relations - only one label given, no language specified
        assert (
            relations[0]["url"]
            == "https://www.admin.ch/opc/de/classified-compilation/19920252/index.html"
        )
        for lang in self.languages:
            assert relations[0]["label"][lang] == "legal_basis"

        # Relations - multilingual labels
        assert relations[1]["url"] == "https://www.example.org/aaa"
        for lang in self.languages:
            assert relations[1]["label"][lang] == f"Text for label {lang.upper()}"

        # Relations - no label given
        assert relations[2]["url"] == "https://www.example.org/bbb"
        for lang in self.languages:
            assert relations[2]["label"][lang] == "https://www.example.org/bbb"

        # Relations - label given, language specified but not German.
        # If there is no label given in a language, we try to get one from
        # another language, in the priority order 'en' -> 'de' -> 'fr' -> 'it'.
        # Here we test that we end up with a label text in all languages, even
        # though the source only had a label in Italian.
        assert relations[3]["url"] == "https://www.example.org/ccc"
        for lang in self.languages:
            assert relations[3]["label"][lang] == "Text for label IT"

        # Qualified relations
        qualified_relations = sorted(
            dataset["qualified_relations"], key=lambda x: x.get("relation")
        )
        assert qualified_relations[0] == {
            "relation": "http://example.org/Original987",
            "had_role": "http://www.iana.org/assignments/relation/original",
        }
        assert qualified_relations[1] == {
            "relation": "http://example.org/Related486",
            "had_role": "http://www.iana.org/assignments/relation/related",
        }

        #  Lists
        assert sorted(dataset["language"]), ["de" == "fr"]
        assert sorted(dataset["groups"]) == [{"name": "gove"}]
        assert sorted(dataset["documentation"]) == [
            "https://example.com/documentation-dataset-1",
            "https://example.com/documentation-dataset-2",
        ]
        assert sorted(dataset["conforms_to"]) == [
            "http://resource.geosciml.org/ontology/timescale/gts",
            "https://inspire.ec.europa.eu/documents",
        ]

        # Dataset URI
        assert (
            extras["uri"]
            == "https://opendata.swiss/dataset/7451e012-64b2-4bbc-af20-a0e2bc61b585"
        )

        # Resources
        assert len(dataset["resources"]) == 1
        resource = dataset["resources"][0]

        #  Simple values
        assert all(
            l in resource["title"] for l in self.languages
        ), "resource title contains all languages"
        assert resource["title"]["fr"] == "Annuaire statistique de la Suisse 1901"
        assert resource["title"]["de"] == ""
        assert all(
            l in resource["description"] for l in self.languages
        ), "resource description contains all languages"
        assert resource["description"]["de"] == ""
        assert resource["format"] == "html"
        assert resource["media_type"] == "text/html"
        assert resource["identifier"] == "346265-fr@bundesamt-fur-statistik-bfs"
        assert resource["license"] == "https://opendata.swiss/terms-of-use#terms_by"
        assert resource["rights"] == "http://www.opendefinition.org/licenses/cc-zero"
        assert resource["language"] == ["fr"]
        assert resource["issued"] == "1900-12-31T00:00:00"
        assert resource["temporal_resolution"] == "P1D"
        assert resource["url"] == "https://www.bfs.admin.ch/asset/fr/hs-b-00.01-jb-1901"
        assert "download_url" not in resource, "download_url not available on resource"

        # Lists
        assert sorted(resource["documentation"]) == [
            "https://example.com/documentation-distribution-1",
            "https://example.com/documentation-distribution-2",
        ]
        assert sorted(resource["access_services"]) == [
            "https://example.com/my-great-data-service-1",
            "https://geoportal.sachsen.de/md/685a4409-a026-430e-afad-1fa2881f9700",
        ]

        # Distribution URI
        assert (
            resource["uri"]
            == "https://opendata.swiss/dataset/7451e012-64b2-4bbc-af20-a0e2bc61b585/resource/c8ec6ca0-6923-4cf3-92f2-95a10e6f8e25"
        )

    def test_dataset_issued_with_year_before_1900(self):

        contents = self._get_file_contents("1894.xml")

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        assert len(datasets) == 1

        dataset = datasets[0]

        # Check date values
        assert dataset["issued"] == "1893-12-31T00:00:00"

        assert dataset["modified"] == "2018-04-24T19:30:57.197374"

    def test_catalog(self):

        contents = self._get_file_contents("catalog.xml")

        p = RDFParser(profiles=["swiss_dcat_ap"])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        assert len(datasets) == 2

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

        assert resource["url"] == "http://access.url.org"
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

        assert resource["url"] == "http://download.url.org"
        assert resource["download_url"] == "http://download.url.org"

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

        assert resource["url"] == "http://access.url.org"
        assert resource["download_url"] == "http://download.url.org"

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
        assert len(dataset["temporals"]) == 10

        assert sorted(dataset["temporals"], key=lambda x: x["start_date"]) == [
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
        ]

    def test_temporals_incorrect_formats(self):
        # See comments in dataset-datetimes-bad.xml for reasons why temporals
        # are mapped/not mapped.
        contents = self._get_file_contents("dataset-datetimes-bad.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        assert len(dataset["temporals"]) == 5

        assert sorted(dataset["temporals"], key=lambda x: x["start_date"]) == [
            {
                "start_date": "2006-11-21T00:00:00",
                "end_date": "2007-11-01T23:59:59.999999",
            },
            {
                "start_date": "2008-01-01T00:00:00",
                "end_date": "2009-12-31T23:59:59.999999",
            },
            {
                "start_date": "2010-04-01T00:00:00",
                "end_date": "2011-05-01T23:59:59.999999",
            },
            {
                "start_date": "2012-11-21T00:00:00",
                "end_date": "2013-11-21T23:59:59.999999",
            },
            {
                "start_date": "2014-04-01T00:00:00",
                "end_date": "2015-01-31T23:59:59.999999",
            },
        ]

    def test_resource_issued_modified_accepted_formats(self):
        contents = self._get_file_contents("dataset-datetimes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]

        issued_dates = [distribution["issued"] for distribution in dataset["resources"]]
        assert sorted(issued_dates) == [
            "1990-01-01T00:00:00",
            "1992-01-02T00:00:00",
            "1994-04-01T00:00:00",
            "1996-01-01T00:00:00",
        ]
        modified_dates = [
            distribution["modified"] for distribution in dataset["resources"]
        ]
        assert sorted(modified_dates) == [
            "1991-04-04T12:30:30",
            "1993-12-03T00:00:00",
            "1995-06-01T00:00:00",
            "1997-01-01T00:00:00",
        ]

    def test_dataset_issued_modified_accepted_formats(self):
        contents = self._get_file_contents("catalog-datetimes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        datasets = [d for d in p.datasets()]

        assert len(datasets) == 4
        issued_dates = [dataset["issued"] for dataset in datasets]
        assert sorted(issued_dates) == [
            "1990-12-31T23:00:00+00:00",
            "1992-12-31T00:00:00",
            "1994-12-01T00:00:00",
            "1996-01-01T00:00:00",
        ]
        modified_dates = [dataset["modified"] for dataset in datasets]
        assert sorted(modified_dates) == [
            "1991-02-19T23:00:00+00:00",
            "1993-02-19T00:00:00",
            "1995-02-01T00:00:00",
            "1997-01-01T00:00:00",
        ]

    def test_multiple_rights_statements(self):
        """Even if there are multiple dct:rights nodes on a distribution, only
        the DCAT-AP CH v1-compatible one should be mapped onto the resource.
        """
        contents = self._get_file_contents("dataset-multiple-rights.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        resource = dataset["resources"][0]

        assert (
            str(resource["rights"])
            == "https://opendata.swiss/terms-of-use#terms_by_ask"
        )

    def test_eu_themes_mapping(self):
        contents = self._get_file_contents("catalog-themes.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)

        for dataset in p.datasets():
            assert sorted(dataset["groups"], key=lambda x: x["name"]) == [
                {"name": "econ"},
                {"name": "gove"},
                {"name": "soci"},
            ]

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
        assert sorted(results) == [
            ("esri_ascii_grid", "text/plain"),
            ("grid_ascii", "text/plain"),
            ("html", "text/html"),
            ("json", "application/json"),
            ("text/calendar", "text/calendar"),
        ]

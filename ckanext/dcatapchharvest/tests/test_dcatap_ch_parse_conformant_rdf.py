import json

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.tests.base_test_classes import BaseParseTest


class TestConformantProfileParse(BaseParseTest):
    def test_dcatap_conformant_landing_page_import(self):
        contents = self._get_file_contents("conformant/dataset-landing-page.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        assert dataset["url"] == "https://www.bfs.admin.ch/bfs/de/home/statistiken.html"

    def test_dcatap_conformant_publisher_import(self):
        contents = self._get_file_contents("conformant/dataset-publisher.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        publisher = json.loads(dataset["publisher"])
        assert publisher["name"] == {
            "fr": "Bureau des economiques",
            "de": "Wirtschaftsamt",
            "en": "",
            "it": "Ufficio economico",
        }
        assert publisher["url"] == "https://some-org.org/info"

    def test_dcatap_conformant_language_import(self):
        contents = self._get_file_contents("conformant/dataset-language.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        assert dataset["language"] == ["de", "en", "fr", "it"]
        assert len(dataset["resources"]) == 1
        assert dataset["resources"][0]["language"] == ["de", "en"]

import json

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.tests.base_test_classes import BaseParseTest


class TestDeprecatedProfileParse(BaseParseTest):
    def test_deprecated_landing_page_import(self):
        contents = self._get_file_contents("deprecated/dataset-landing-page.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        assert dataset["url"] == "http://www.bafu.admin.ch/laerm/index.html?lang=de"

    def test_deprecated_publisher_import(self):
        contents = self._get_file_contents("deprecated/dataset-publisher.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        publisher = json.loads(dataset["publisher"])
        assert publisher["name"] == "Bundesamt für Landestopografie swisstopo"
        assert publisher["url"] == ""

    def test_deprecated_language_import(self):
        contents = self._get_file_contents("deprecated/dataset-language.xml")
        p = RDFParser(profiles=["swiss_dcat_ap"])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        assert dataset["language"] == ["de", "en", "fr", "it"]
        assert len(dataset["resources"]) == 1
        assert dataset["resources"][0]["language"] == ["de", "en"]

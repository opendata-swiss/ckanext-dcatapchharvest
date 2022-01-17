# -*- coding: utf-8 -*-

from datetime import datetime
import unittest

import nose
import json

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.tests.utils import get_file_contents, get_dataset_extras

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class NonConformantProfileParseTest(unittest.TestCase):
    """test parsing of datacatalog with deprecated structure (DCAT-AP CH Version 1)"""
    def setUp(self):
        if not hasattr(self, 'datasets'):
            contents = get_file_contents('catalog-deprecated.xml')
            p = RDFParser(profiles=['swiss_dcat_ap'])
            p.parse(contents)
            self.datasets = [d for d in p.datasets()]
            self.dataset = [d for d in self.datasets if d['identifier'] == "123@swisstopo"][0]

    def test_deprecated_landing_page(self):
        """check that landing page is set"""
        eq_(self.dataset['url'], u"https://www.bfs.admin.ch/bfs/de/home/statistiken.html")

    def test_deprecated_publisher(self):
        """check that publisher is set"""
        publisher = json.loads(self.dataset['publisher'])
        eq_(publisher['url'], u"https://www.bafu.admin.ch/")
        eq_(publisher['name'], u"Bundesamt für Landestopografie swisstopo")

    def test_dataset_without_description(self):
        assert all(l in self.dataset['description'] for l in ['de', 'fr', 'it', 'en']), "description contains all languages"
        eq_(self.dataset['description']['de'], u'')

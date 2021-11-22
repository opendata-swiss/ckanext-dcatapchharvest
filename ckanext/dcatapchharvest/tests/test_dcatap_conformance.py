# -*- coding: utf-8 -*-

import os
from datetime import datetime

import nose

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.profiles import (DCAT, DCT)

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class BaseParseTest(object):
    def _get_file_contents(self, file_name):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures',
                            file_name)
        with open(path, 'r') as f:
            return f.read()


class TestSwissDCATAPProfileParsing(BaseParseTest):
    def setUp(self):
        contents = self._get_file_contents('catalog-dcatap-conform.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        self.datasets = datasets = [d for d in p.datasets()]
        self.dataset = datasets[0]

    def test_dcatap_conformant_landing_page_import(self):
        eq_(self.dataset['url'], u"https://www.bfs.admin.ch/bfs/de/home/statistiken.html")

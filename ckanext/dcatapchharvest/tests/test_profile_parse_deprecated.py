# -*- coding: utf-8 -*-

import unittest

import nose

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.tests.utils import get_file_contents, get_dataset_extras

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class DeprecatedProfileParseTest(unittest.TestCase):
    """test parsing of datacatalog DCAT-AP CH Version 2 classes
    and properties"""
    def test_mapping_of_landing_page_from_string(self):
        """"test the pick up of all landing page when given as string"""
        contents = get_file_contents('deprecated/dataset-landing-page.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        eq_(dataset['url'], u"https://www.bfs.admin.ch/bfs/de/home/statistiken.html")

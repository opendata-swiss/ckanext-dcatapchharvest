# -*- coding: utf-8 -*-

from datetime import datetime
import unittest

import nose

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.tests.utils import get_file_contents, get_dataset_extras

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class ProfileParseTest(unittest.TestCase):
    """tests parsing of deprecated DCAT-AP CH
    Version 1 classes and properties"""
    def test_mapping_of_landing_page_from_uri(self):
        """"test the pick up of all landing page when given as string"""
        contents = get_file_contents('deprecated/dataset-landing-page.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        eq_(dataset['url'], u"http://www.bafu.admin.ch/laerm/index.html?lang=de")

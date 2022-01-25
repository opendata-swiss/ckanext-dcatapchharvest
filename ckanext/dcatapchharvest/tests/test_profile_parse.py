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
    Version 2 classes and properties"""
    def test_mapping_of_landing_page_from_uri(self):
        contents = get_file_contents('deprecated/dataset-landing-page.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        eq_(dataset['url'], u"http://www.bafu.admin.ch/laerm/index.html?lang=de")

    def test_mapping_of_contact_point(self):
        contents = get_file_contents('deprecated/dataset-contact-point.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        contact_point1 = dataset['contact_points'][0]
        contact_point2 = dataset['contact_points'][0]
        eq_(contact_point1['name'], 'Abteilung Lärm BAFU')
        eq_(contact_point1['email'], 'noise@bafu.admin.ch')
        eq_(contact_point1['name'], 'Abteilung Lärm BAFU')
        eq_(contact_point1['email'], 'noise@bafu.admin.ch')
        
        eq_(dataset['contact_points'], u"http://www.bafu.admin.ch/laerm/index.html?lang=de")
        <vcard:fn>Abteilung Lärm BAFU</vcard:fn>
        <vcard:hasEmail rdf:resource="mailto:noise@bafu.admin.ch"/>
      </vcard:Organization>
    </dcat:contactPoint>

    <dcat:contactPoint>
      <vcard:Individual>
        <vcard:fn>Sekretariat BAFU</vcard:fn>
        <vcard:hasEmail rdf:resource="mailto:sekretariat@bafu.admin.ch"/>
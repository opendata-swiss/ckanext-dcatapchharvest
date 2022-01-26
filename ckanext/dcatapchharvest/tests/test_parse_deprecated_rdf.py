# -*- coding: utf-8 -*-

import os
import nose
import json
from ckanext.dcat.processors import RDFParser

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class BaseParseTest(object):
    def _get_file_contents(self, file_name):
        path = os.path.join(os.path.dirname(__file__),
                            'fixtures',
                            file_name)
        with open(path, 'r') as f:
            return f.read()


class DeprecatedProfileParseTest(BaseParseTest):
    def test_deprecated_landing_page_import(self):
        contents = self._get_file_contents('deprecated/dataset-landing-page.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        eq_(dataset['url'], u"https://www.bfs.admin.ch/bfs/de/home/statistiken.html")

    def test_deprecated_publisher_import(self):
        contents = self._get_file_contents('deprecated/dataset-publisher.xml')
        p = RDFParser(profiles=['swiss_dcat_ap'])
        p.parse(contents)
        dataset = [d for d in p.datasets()][0]
        publisher = json.loads(dataset['publisher'])
        eq_(publisher['name'], 'Landesamt Topographie Swisstopo')
        eq_(publisher['url'], 'https://swisstopo')

# -*- coding: utf-8 -*-

from datetime import datetime
import json
import nose
import unittest

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapchharvest.tests.utils import get_file_contents

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class ConformantProfileParseTest(unittest.TestCase):
    """test parsing of datacatalog that conforms DCATAP"""
    def setUp(self):
        if not hasattr(self, 'datasets'):
            contents = get_file_contents('catalog-dcatap.xml')
            p = RDFParser(profiles=['swiss_dcat_ap'])
            p.parse(contents)
            self.datasets = [d for d in p.datasets()]
            self.dataset = [d for d in self.datasets if d['identifier'] == "123@swisstopo"][0]
            self.dataset_old = [d for d in self.datasets if d['identifier'] == "before1900@swisstopo"][0]

    def test_datasets_are_found(self):
        """check that all datasets are found"""
        eq_(len(self.datasets), 2)

    def test_landing_page(self):
        """check that landing page is set"""
        eq_(self.dataset['url'], u"https://www.bfs.admin.ch/bfs/de/home/statistiken.html")

    def test_publisher(self):
        """check that the publisher is set"""
        publisher = json.loads(self.dataset['publisher'])
        eq_(publisher['url'], u"https://swisstopo")
        eq_(publisher['name'], u"Landesamt für Topographie Swisstopo")

    def test_date_before_1900(self):
        """check issued before 1900"""
        eq_(self.dataset_old['issued'], -2398377600)
        issued = datetime.fromtimestamp(self.dataset_old['issued'])
        eq_(issued.date().isoformat(), u'1893-12-31')

    def test_issued_as_xsd_datetime(self):
        """test the pick up of issued as string typed as xsd:datetime"""
        eq_(self.dataset['issued'], 1492992000)
        issued = datetime.fromtimestamp(self.dataset['issued'])
        eq_(issued.date().isoformat(), u'2017-04-24')

    def test_modified_as_xsd_datetime(self):
        """test the pick up of issued as string typed as xsd:datetime"""
        eq_(self.dataset['modified'], 1524528000)
        modified = datetime.fromtimestamp(self.dataset['modified'])
        eq_(modified.date().isoformat(), u'2018-04-24')

    def test_dataset_keywords(self):
        """test the pick up of keywords in the 4 languages de, fr, en, and it
        they are stored as both keywords and tags on the dataset"""
        assert all(l in self.dataset['keywords'] for l in ['de', 'fr', 'it', 'en']), "keywords contains all languages"
        eq_(sorted(self.dataset['keywords']['de']), ['publikation', 'statistische-grundlagen-und-ubersichten'])
        eq_(sorted(self.dataset['keywords']['fr']), ['bases-statistiques-et-generalites', 'publication'])
        eq_(sorted(self.dataset['keywords']['it']), ['basi-statistiche-e-presentazioni-generali', 'pubblicazione'])
        eq_(sorted(self.dataset['keywords']['en']), ['publication', 'statistical-basis-and-overviews'])
        eq_(sorted(self.dataset['tags'], key=lambda k: k['name']), [{'name': 'basas-statisticas-e-survistas'},
                                                                    {'name': 'bases-statistiques-et-generalites'},
                                                                    {'name': 'basi-statistiche-e-presentazioni-generali'},
                                                                    {'name': 'pubblicazione'},
                                                                    {'name': 'publication'},
                                                                    {'name': 'publication'},
                                                                    {'name': 'publikation'},
                                                                    {'name': 'statistical-basis-and-overviews'},
                                                                    {'name': 'statistische-grundlagen-und-ubersichten'}])

    def test_dataset_title(self):
        """test the pick up of the title in the 4 languages de, fr, en, and it
        A language dictionary is formed with the languages as keys"""
        assert all(l in self.dataset['title'] for l in ['de', 'fr', 'it', 'en']), "title contains all languages"
        eq_(self.dataset['title']['de'], u'Statistisches Jahrbuch der Schweiz 1901')
        eq_(self.dataset['title']['fr'], u'Annuaire statistique de la Suisse 1901')

    def test_dataset_description(self):
        """test the pick up of the description in the 4 languages de, fr, en, and it
        A language dictionary is formed with the languages as keys"""
        assert all(l in self.dataset['description'] for l in ['de', 'fr', 'it', 'en']), "description contains all languages"
        eq_(self.dataset['description']['de'], u'In diesem Dataset finden Sie Daten zum Waldbestand Zürichs')
        eq_(self.dataset['description']['en'], u'This dataset contains information regarding the forests in Canton Zurich')

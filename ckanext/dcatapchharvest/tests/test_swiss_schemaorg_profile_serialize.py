import json

import nose

from rdflib import Literal
from rdflib.namespace import RDF

from ckanext.dcat import utils
from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import SCHEMA

from rdflib import URIRef
import ckanext.dcatapchharvest.dcat_helpers as dh

from ckanext.dcat.tests.test_euro_dcatap_profile_serialize import BaseSerializeTest
import logging

log = logging.getLogger(__name__)

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class TestSchemaOrgProfileSerializeDataset(BaseSerializeTest):

    def test_graph_from_dataset(self):

        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Test DCAT dataset',
            'url': 'http://example.com/ds1',
            'version': '1.0b',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774',
            'keywords':
                {
                    'fr': [],
                    'de': [
                        'alter',
                        'sozialhilfe'
                    ],
                    'en': [
                        'age'
                    ],
                    'it': []
                },
            'groups': [
                {
                    'display_name':
                        {
                            'fr': 'Economie nationale',
                            'de': 'Volkswirtschaft',
                            'en': 'National economy',
                            'it': 'Economia'
                        },
                    'description':
                        {
                            'fr': '',
                            'de': '',
                            'en': 'some descriptiom'
                                  '',
                            'it': ''
                        },
                    'image_display_url': '',
                    'title':
                        {
                            'fr': 'Economie nationale',
                            'de': 'Volkswirtschaft',
                            'en': 'National economy',
                            'it': 'Economia'
                        },
                    'id': '5389c3f2-2f64-436b-9fac-2d1fc342f7b5',
                    'name': 'national-economy'
                },
                {
                    'display_name':
                        {
                            'fr': 'Education, science',
                            'de': 'Bildung, Wissenschaft',
                            'en': 'Education and science',
                            'it': 'Formazione e scienza'
                        },
                    'description':
                        {
                            'fr': '',
                            'de': '',
                            'en': '',
                            'it': ''
                        },
                    'image_display_url': '',
                    'title':
                        {
                            'fr': 'Education, science',
                            'de': 'Bildung, Wissenschaft',
                            'en': 'Education and science',
                            'it': 'Formazione e scienza'
                        },
                    'id': 'afcb4a2a-b4b0-4d7c-984a-9078e964be49',
                    'name': 'education'
                },
                {
                    'display_name':
                        {
                            'fr': 'Finances',
                            'de': 'Finanzen',
                            'en': 'Finances',
                            'it': 'Finanze'
                        },
                    'description':
                        {
                            'fr': '',
                            'de': '',
                            'en': '',
                            'it': ''
                        },
                    'image_display_url': '',
                    'title':
                        {
                            'fr': 'Finances',
                            'de': 'Finanzen',
                            'en': 'Finances',
                            'it': 'Finanze'
                        },
                    'id': '79cbe120-e9c6-4249-b934-58ca980606d7',
                    'name': 'finances'
                }
            ],
            'description': {
                'fr': '',
                'de': 'Deutsche Beschreibung',
                'en': 'English Description',
                'it': ''
            },
            'extras': [
                {'key': 'alternate_identifier', 'value': '[\"xyz\", \"abc\"]'},
                {'key': 'identifier', 'value': '26be5452-fc5c-11e7-8450-fea9aa178066'},
                {'key': 'version_notes', 'value': 'This is a beta version'},
                {'key': 'frequency', 'value': 'monthly'},
                {'key': 'language', 'value': '[\"en\"]'},
                {'key': 'theme', 'value': '[\"http://eurovoc.europa.eu/100142\", \"http://eurovoc.europa.eu/100152\"]'},
                {'key': 'conforms_to', 'value': '[\"Standard 1\", \"Standard 2\"]'},
                {'key': 'access_rights', 'value': 'public'},
                {'key': 'documentation', 'value': '[\"http://dataset.info.org/doc1\", \"http://dataset.info.org/doc2\"]'},
                {'key': 'provenance', 'value': 'Some statement about provenance'},
                {'key': 'dcat_type', 'value': 'test-type'},
                {'key': 'related_resource', 'value': '[\"http://dataset.info.org/related1\", \"http://dataset.info.org/related2\"]'},
                {'key': 'has_version', 'value': '[\"https://data.some.org/catalog/datasets/derived-dataset-1\", \"https://data.some.org/catalog/datasets/derived-dataset-2\"]'},
                {'key': 'is_version_of', 'value': '[\"https://data.some.org/catalog/datasets/original-dataset\"]'},
                {'key': 'source', 'value': '[\"https://data.some.org/catalog/datasets/source-dataset-1\", \"https://data.some.org/catalog/datasets/source-dataset-2\"]'},
                {'key': 'sample', 'value': '[\"https://data.some.org/catalog/datasets/9df8df51-63db-37a8-e044-0003ba9b0d98/sample\"]'},
            ]
        }
        extras = self._extras(dataset)

        s = RDFSerializer(profiles=['swiss_schemaorg'])
        g = s.g

        dataset_ref = s.graph_from_dataset(dataset)

        eq_(unicode(dataset_ref), utils.dataset_uri(dataset))

        # Basic fields
        assert self._triple(g, dataset_ref, RDF.type, SCHEMA.Dataset)
        assert self._triple(g, dataset_ref, SCHEMA.name, dataset['title'])
        assert self._triple(g, dataset_ref, SCHEMA.version, dataset['version'])
        assert self._triple(g, dataset_ref, SCHEMA.identifier, extras['identifier'])

        # Dates
        assert self._triple(g, dataset_ref, SCHEMA.datePublished, dataset['metadata_created'])
        assert self._triple(g, dataset_ref, SCHEMA.dateModified, dataset['metadata_modified'])

        for key, value in dataset['description'].iteritems():
            if dataset['description'].get(key):
                assert self._triple(g, dataset_ref, SCHEMA.description, Literal(value, lang=key))
        eq_(len([t for t in g.triples((dataset_ref, SCHEMA.description, None))]), 2)

        # Tags
        eq_(len([t for t in g.triples((dataset_ref, SCHEMA.keywords, None))]), 3)
        for key, keywords in dataset['keywords'].iteritems():
            if dataset['keywords'].get(key):
                for keyword in keywords:
                    assert self._triple(g, dataset_ref, SCHEMA.keywords, Literal(keyword, lang=key))

        # List
        for item in [
            ('language', SCHEMA.inLanguage, Literal),
        ]:
            values = json.loads(extras[item[0]])
            eq_(len([t for t in g.triples((dataset_ref, item[1], None))]), len(values))
            for value in values:
                assert self._triple(g, dataset_ref, item[1], item[2](value))

    # new test
    def test_graph_from_dataset_uri(self):

        dataset = {
            'id': '4b6fe9ca-dc77-4cec-92a4-55c6624a5bd6',
            'name': 'test-dataset',
            'title': 'Test DCAT dataset',
            'uri': 'https://test.example.com/dataset/foo',
            #'url': 'http://example.com/ds1',
            'version': '1.0b',
            'metadata_created': '2015-06-26T15:21:09.034694',
            'metadata_modified': '2015-06-26T15:21:09.075774'
        }
        resources = {
            "package_id": "bb14c897-eca0-47d0-a599-ae2e6faf839d",
            "id": "bb957832-dad6-49d0-8096-4b245be196db",
            "uri": "https://test.example.com/dataset/foo",
            "revision_id": "be9bfa8a-6b2c-473c-8cc0-bb4b7391d500",
            "identifier": "1c8d829b-0ce2-4d2d-ab54-f952d0f3818c",
        }
        s = RDFSerializer(profiles=['swiss_schemaorg'])
        g = s.g
        # Change dataset uri that includes a test url
        dataset['uri'] = dh.dataset_uri(dataset)
        dataset_ref = s.graph_from_dataset(dataset)

        # Change resource uri that includes a test url
        resources['uri'] = dh.resource_uri(resources)
        distribution = URIRef(resources['uri'])

        log.info("Checking resource_uri '%r'" % resources["uri"])
        log.info("Checking distribution '%r'" % distribution)
        g.add((dataset_ref, SCHEMA.distribution, distribution))
        g.add((distribution, RDF.type, SCHEMA.Distribution))

        #log.info(" 3 Checking dataset_ref dict '%r'" %= URIRef(dh.resource_uri(dataset.get('resources', []))))
        # New Resource for datsets with changed uri
        #dataset_ref_changed = URIRef(dataset_uri)

        #for resource_dict in dataset.get('resources', []):
        log.info("Checking resource_dict '%r'1: " % resources)

        log.info("! Checking dataset_ref '%r'" % dataset_ref)

        log.info("Checking dataset_ref '%r'" % dataset_ref)
        log.info("Checking g '%r'" % g)
        log.info("Checking RDF.type '%r'" % RDF.type)
        log.info("Checking RDF '%r'" % RDF)
        log.info("Checking SCHEMA.distribution'%r'" % SCHEMA.distribution)
        log.info("Checking SCHEMA.Dataset'%r'" % SCHEMA.Dataset)
        log.info("Checking SCHEMA.url '%r'" % SCHEMA.url)
        log.info("Checking SCHEMA.uri '%r'" % SCHEMA.uri)
        log.info("Checking dataset['uri'] '%r'" % dataset['uri'])
        #eq_(unicode(dataset_ref), utils.dataset_uri(dataset))

            # Basic fields

        assert self._triple(g, dataset_ref, RDF.type, SCHEMA.Dataset)
        #assert self._triple(g, dataset_ref, SCHEMA.url, dataset['uri'])
        assert self._triple(g, dataset_ref, SCHEMA.name, dataset['title'])
        assert self._triple(g, dataset_ref, SCHEMA.version, dataset['version'])
        assert self._triple(g, dataset_ref, RDF.type, SCHEMA.distribution)

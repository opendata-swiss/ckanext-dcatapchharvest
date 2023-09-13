import json

import nose

from rdflib import Literal
from rdflib.namespace import RDF

from ckanext.dcat import utils
from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import FOAF, SCHEMA

from rdflib import URIRef
import ckanext.dcatapchharvest.dcat_helpers as dh

from ckanext.dcatapchharvest.tests.base_test_classes import BaseSerializeTest

import logging
log = logging.getLogger(__name__)

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true


class TestSchemaOrgProfileSerializeDataset(BaseSerializeTest):

    def test_graph_from_dataset(self):

        dataset = json.loads(
            self._get_file_contents('dataset.json')
        )
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
        assert self._triple(g, dataset_ref, SCHEMA.datePublished, dataset['issued'])
        assert len(list(g.objects(dataset_ref, SCHEMA.dateModified))) == 0

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
            # ('documentation', FOAF.page, URIRef, FOAF.Document),
        ]:
            values = json.loads(extras[item[0]])
            log.warning(values)
            eq_(len([t for t in g.triples((dataset_ref, item[1], None))]), len(values))
            for value in values:
                assert self._triple(g, dataset_ref, item[1], item[2](value))

    def test_graph_from_dataset_uri(self):
        """"Tests that datasets (resources) with a uri from the test system
        have that uri changed to reference the prod system when they are output as a graph"""

        dataset = json.loads(
            self._get_file_contents('dataset-test-uri.json')
        )

        s = RDFSerializer(profiles=['swiss_dcat_ap'])
        g = s.g
        dataset_ref = s.graph_from_dataset(dataset)

        # Change dataset uri that includes a test url
        dataset_uri = dh.dataset_uri(dataset, dataset_ref)
        dataset_ref_changed = URIRef(dataset_uri)

        # Test that the distribution is present in the graph with the new resource uri
        for resource_dict in dataset.get("resources", []):
            distribution = URIRef(dh.resource_uri(resource_dict))

        # Basic fields
        assert self._triple(g, dataset_ref_changed, RDF.type, SCHEMA.Dataset)
        assert self._triple(g, dataset_ref_changed, SCHEMA.name, dataset['title'])
        assert self._triple(g, dataset_ref_changed, SCHEMA.version, dataset['version'])
        assert self._triple(g, distribution, RDF.type, SCHEMA.Distribution)

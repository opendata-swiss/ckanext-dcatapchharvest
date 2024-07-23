import json

import logging

import nose

from rdflib import URIRef, Literal, XSD
from rdflib.namespace import RDF

from ckanext.dcat import utils
from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import DCAT, DCT, FOAF, OWL, SCHEMA, VCARD, XSD

import ckanext.dcatapchharvest.dcat_helpers as dh

from ckanext.dcatapchharvest.tests.base_test_classes import BaseSerializeTest

eq_ = nose.tools.eq_
assert_true = nose.tools.assert_true
log = logging.getLogger(__name__)


class TestDCATAPCHProfileSerializeDataset(BaseSerializeTest):

    def test_graph_from_dataset(self):

        dataset = json.loads(
            self._get_file_contents('dataset.json')
        )
        extras = self._extras(dataset)

        s = RDFSerializer(profiles=['swiss_dcat_ap'])
        g = s.g

        dataset_ref = s.graph_from_dataset(dataset)

        eq_(unicode(dataset_ref), utils.dataset_uri(dataset))

        # Basic fields
        assert self._triple(g, dataset_ref, RDF.type, DCAT.Dataset)
        assert self._triple(g, dataset_ref, DCT.title, dataset['title'])
        assert self._triple(g, dataset_ref, OWL.versionInfo, dataset['version'])
        assert self._triple(g, dataset_ref, DCT.identifier, extras['identifier'])

        # Dates
        assert self._triple(g, dataset_ref, DCT.issued, dataset['issued'], XSD.dateTime)
        assert len(list(g.objects(dataset_ref, DCT.modified))) == 0

        for key, value in dataset['description'].iteritems():
            if dataset['description'].get(key):
                assert self._triple(g, dataset_ref, DCT.description, Literal(value, lang=key))
        eq_(len([t for t in g.triples((dataset_ref, DCT.description, None))]), 2)

        # Tags
        eq_(len([t for t in g.triples((dataset_ref, DCAT.keyword, None))]), 3)
        for key, keywords in dataset['keywords'].iteritems():
            if dataset['keywords'].get(key):
                for keyword in keywords:
                    assert self._triple(g, dataset_ref, DCAT.keyword, Literal(keyword, lang=key))

        # Documentation
        eq_(len([t for t in g.triples((dataset_ref, FOAF.page, None))]), 2)
        for documentation_link in dataset['documentation']:
            assert self._triple(g, dataset_ref, FOAF.page, URIRef(documentation_link))

        # Contact points
        eq_(len([t for t in g.triples((dataset_ref, DCAT.contactPoint, None))]), 1)

        contact_point = next(g.objects(dataset_ref, DCAT.contactPoint))
        eq_(next(g.objects(contact_point, RDF.type)), VCARD.Organization)
        eq_(
            next(g.objects(contact_point, VCARD.hasEmail)),
            URIRef("mailto:maria.muster@example.com")
        )
        eq_(next(g.objects(contact_point, VCARD.fn)), Literal("Maria Muster"))

        # Conformance
        conforms_to = dataset.get("conforms_to", [])
        # Check if the number of triples matches the number of conformance uris
        eq_(
            len(list(g.triples((dataset_ref, DCT.conformsTo, None)))),
            len(conforms_to)
        )
        for link in conforms_to:
            # Check if the triple (dataset_ref, DCT.conformsTo, URIRef(link)) exists in the graph
            assert (dataset_ref, DCT.conformsTo, URIRef(link)) in g

        # List
        for item in [
            ('language', DCT.language, Literal),
        ]:
            values = json.loads(extras[item[0]])
            eq_(len([t for t in g.triples((dataset_ref, item[1], None))]), len(values))
            for value in values:
                assert self._triple(g, dataset_ref, item[1], item[2](value))

        # Resources
        eq_(len([t for t in g.triples((dataset_ref, DCAT.distribution, None))]), len(dataset["resources"]))
        for resource_dict in dataset.get("resources", []):
            distribution = URIRef(dh.resource_uri(resource_dict))
            assert self._triple(g, distribution, RDF.type, DCAT.Distribution)
            for link in resource_dict.get("documentation", []):
                assert self._triple(g, distribution, FOAF.page, URIRef(link))

            eq_(
                len([t for t in g.triples((distribution, DCAT.accessService, None))]),
                len(resource_dict.get("access_services", []))
            )
            for link in resource_dict.get("access_services", []):
                assert self._triple(g, distribution, DCAT.accessService, URIRef(link))

            # e2c50e70-67ad-4f86-bb1b-3f93867eadaa
            if resource_dict.get('rights') == 'Creative Commons Zero 1.0 Universal (CC0 1.0)':
                assert self._triple(g, distribution, DCT.rights, URIRef("https://creativecommons.org/publicdomain/zero/1.0/"))

            if resource_dict.get('license') == 'NonCommercialAllowed-CommercialAllowed-ReferenceNotRequired':
                assert self._triple(g, distribution, DCT.license, URIRef("http://dcat-ap.ch/vocabulary/licenses/terms_open"))

            # 28e75e40-e1a1-497b-a1b9-8c1834d60201
            if resource_dict.get('rights') == "http://dcat-ap.ch/vocabulary/licenses/terms_by":
                assert self._triple(g, distribution, DCT.rights, URIRef("http://dcat-ap.ch/vocabulary/licenses/terms_by"))

            if resource_dict.get('license') == "NonCommercialAllowed-CommercialAllowed-ReferenceRequired":
                assert self._triple(g, distribution, DCT.license, URIRef("http://dcat-ap.ch/vocabulary/licenses/terms_by"))

            # 0cfce6ba-28f4-4229-b733-f6492c650395
            if resource_dict.get('rights') == "http://dcat-ap.ch/vocabulary/licenses/terms_by_ask":
                assert self._triple(g, distribution, DCT.rights, URIRef("http://dcat-ap.ch/vocabulary/licenses/terms_by_ask"))

            if resource_dict.get('license') == "https://creativecommons.org/licenses/by/4.0/":
                assert self._triple(g, distribution, DCT.license, URIRef("https://creativecommons.org/licenses/by/4.0/"))

            if resource_dict.get('format') == "CSV":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/CSV"))

            if resource_dict.get('format') == "HTML":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/HTML"))

            if resource_dict.get('format') == "RDF N-Triples":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/RDF_N_TRIPLES"))

            if resource_dict.get('format') == "JSON-LD":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/JSON_LD"))

            if resource_dict.get('format') == "ESRI ASCII Grid":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/GRID_ASCII"))

            if resource_dict.get('format') == "WORLDFILE":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/WORLD"))

            if resource_dict.get('format') == "WCS":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://publications.europa.eu/resource/authority/file-type/WCS_SRVC"))

            if resource_dict.get('media_type') == "application/1d-interleaved-parityfec":
                assert self._triple(g, distribution, DCAT.mediaType, URIRef("http://www.iana.org/assignments/media-types/application/1d-interleaved-parityfec"))

            if resource_dict.get('format') == "application/1d-interleaved-parityfec":
                assert self._triple(g, distribution, DCT['format'], URIRef("http://www.iana.org/assignments/media-types/application/1d-interleaved-parityfec"))

            if resource_dict.get('temporal_resolution') == "P1D":
                expected_literal = Literal("P1D", datatype=XSD.duration)
                assert self._triple(g, distribution, DCAT.temporalResolution, expected_literal)


    def test_graph_from_dataset_uri(self):
        """Tests that datasets (resources) with a uri from the test system
        have that uri changed to reference the prod system when they are output
        as a graph
        """

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
        assert self._triple(g, dataset_ref_changed, RDF.type, DCAT.Dataset)
        assert self._triple(g, dataset_ref_changed, DCT.title, dataset['title'])
        assert self._triple(g, dataset_ref_changed, OWL.versionInfo, dataset['version'])
        assert self._triple(g, distribution, RDF.type, DCAT.Distribution)

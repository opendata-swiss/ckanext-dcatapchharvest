import iribaker
import json
import os
from urllib.parse import urlparse
from ckantoolkit import config
from rdflib import URIRef, Graph
from rdflib.namespace import Namespace, RDF, SKOS
import xml.etree.ElementTree as ET
import logging

log = logging.getLogger(__name__)

DCT = Namespace("http://purl.org/dc/terms/")
EUTHEMES = \
    Namespace("http://publications.europa.eu/resource/authority/data-theme/")
HYDRA = Namespace('http://www.w3.org/ns/hydra/core#')

SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

frequency_namespaces = {
  "skos": SKOS,
  "dct": DCT,
}

format_namespaces = {
  "skos": SKOS,
  "rdf": RDF,
}

media_types_namespaces = {
    'ns': 'http://www.iana.org/assignments'
}

license_namespaces = {
  "skos": SKOS,
  "dct": DCT,
  "skosxl": SKOSXL,
  "rdf": RDF,
  "rdfs": RDFS,
}

theme_namespaces = {
    "euthemes": EUTHEMES,
    "skos": SKOS,
    "dct": DCT,
    "rdf": RDF,
}

__location__ = \
    os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def uri_to_iri(uri):
    """
    convert URI to IRI (used for RDF)
    this function also validates the URI and throws a ValueError if the
    provided URI is invalid
    """
    if not uri:
        raise ValueError("Provided URI is empty or None")

    result = urlparse(uri)
    if not result.scheme or not result.netloc or result.netloc == '-':
        raise ValueError("Provided URI does not have a valid schema or netloc")

    try:
        iri = iribaker.to_iri(uri)
        return iri
    except Exception as e:
        raise ValueError("Provided URI can't be converted to IRI: %s" % e)


def get_langs():
    language_priorities = ['en', 'de', 'fr', 'it']
    return language_priorities


def dataset_uri(dataset_dict, dataset_ref=None):
    """
    Returns a URI for the dataset

    This is a hack/workaround for the use case where data publishers create
    datsets on the test environment, export them to XML and then import them
    to the production site. In that case, the dataset uris will contain the
    url of the test environment, so we have to replace it with the prod one.
    """
    uri = (str(dataset_ref)
           if isinstance(dataset_ref, URIRef)
           else '')
    if not uri:
        uri = dataset_dict.get('uri', '')
    if not uri:
        for extra in dataset_dict.get('extras', []):
            if extra['key'] == 'uri' and extra['value'] != 'None':
                uri = extra['value']
                break
    test_env_url_string = config.get(
        'ckanext.dcat_ch_rdf_harvester.test_env_urls', '')
    if len(test_env_url_string) > 0:
        for test_url in test_env_url_string.split(','):
            if test_url in uri:
                uri = ''
                break
    if not uri:
        uri = get_permalink(dataset_dict.get('identifier'))

    return uri


def get_permalink(identifier):
    site_url = config.get('ckan.site_url')
    return '{0}/perma/{1}'.format(site_url, identifier)


def resource_uri(resource_dict, distribution=None):
    """
    Returns a URI for the resource

    This is a hack/workaround for the use case where data publishers create
    datsets on the test environment, export them to XML and then import them
    to the production site. In that case, the resource uri will contain the
    url of the test environment, so we have to replace it with the prod one.

    If this function is called when importing the resource, it just removes
    test-environment uri. We can't generate the new one yet as the dataset and
    resource haven't been saved. This is all right as it will be generated
    when the dataset is output in RDF format.
    """
    uri = (str(distribution)
           if isinstance(distribution, URIRef)
           else '')
    if not uri:
        uri = resource_dict.get('uri', '')
    if uri:
        test_env_url_string = config.get(
            'ckanext.dcat_ch_rdf_harvester.test_env_urls', '')
        if len(test_env_url_string) > 0:
            for test_url in test_env_url_string.split(','):
                if test_url in uri:
                    uri = ''
                    break
    if not uri or uri == 'None':
        site_url = config.get('ckan.site_url')
        dataset_id = resource_dict.get('package_id')
        resource_id = resource_dict.get('id')
        if dataset_id and resource_id:
            uri = '{0}/dataset/{1}/resource/{2}'.format(site_url.rstrip('/'),
                                                        dataset_id,
                                                        resource_dict['id'])
    return uri


def get_frequency_values():
    g = Graph()
    frequency_mapping = {}
    for prefix, namespace in list(frequency_namespaces.items()):
        g.bind(prefix, namespace)
    file = os.path.join(__location__, 'frequency.ttl')
    g.parse(file, format='turtle')
    for ogdch_frequency_ref in g.subjects(predicate=RDF.type,
                                          object=SKOS.Concept):
        frequency_mapping[ogdch_frequency_ref] = None
        for obj in g.objects(subject=ogdch_frequency_ref,
                             predicate=SKOS.exactMatch):
            frequency_mapping[ogdch_frequency_ref] = obj
    return frequency_mapping


def get_license_uri_by_name(vocabulary_name):
    license_vocabulary = get_license_values()
    for key, value in list(license_vocabulary.items()):
        if str(vocabulary_name) == str(value):
            return key
    return None


def get_license_name_by_uri(vocabulary_uri):
    license_vocabulary = get_license_values()
    for key, value in list(license_vocabulary.items()):
        if str(vocabulary_uri) == str(key):
            return str(value)
    return None


def get_license_values():
    g = Graph()
    license_mapping = {}
    for prefix, namespace in list(license_namespaces.items()):
        g.bind(prefix, namespace)
    file = os.path.join(__location__, 'license.ttl')
    g.parse(file, format='turtle')
    for ogdch_license_ref in g.subjects(predicate=RDF.type,
                                        object=SKOS.Concept):
        license_mapping[ogdch_license_ref] = None
        for license_pref_label in g.objects(subject=ogdch_license_ref,
                                            predicate=SKOSXL.prefLabel):
            for license_literal in g.objects(subject=license_pref_label,
                                             predicate=SKOSXL.literalForm):
                license_mapping[ogdch_license_ref] = license_literal
    return license_mapping


def get_theme_mapping():
    g = Graph()
    theme_mapping = {}
    for prefix, namespace in list(theme_namespaces.items()):
        g.bind(prefix, namespace)
    file = os.path.join(__location__, 'themes.ttl')
    g.parse(file, format='turtle')
    for ogdch_theme_ref in g.subjects(predicate=RDF.type,
                                      object=SKOS.Concept):
        theme_mapping[ogdch_theme_ref] = [
            obj
            for obj in g.objects(subject=ogdch_theme_ref,
                                 predicate=SKOS.mappingRelation)
            if g.namespace_manager.compute_qname(obj)[0] == 'euthemes']
    return theme_mapping


def get_pagination(catalog_graph):
    pagination = {}
    for pagination_node in catalog_graph.subjects(
            RDF.type, HYDRA.PagedCollection
    ):
        items = [
            ('next', HYDRA.nextPage),
            ('first', HYDRA.firstPage),
            ('last', HYDRA.lastPage),
            ('count', HYDRA.totalItems),
            ('items_per_page', HYDRA.itemsPerPage),
        ]
        for key, ref in items:
            for obj in catalog_graph.objects(pagination_node, ref):
                pagination[key] = str(obj)
    return pagination


def get_format_values():
    g = Graph()
    for prefix, namespace in list(format_namespaces.items()):
        g.bind(prefix, namespace)
    file = os.path.join(__location__, 'formats.xml')
    g.parse(file, format='xml')
    format_values = {}
    for format_uri_ref in g.subjects():
        format_extension = format_uri_ref.split('/')[-1].lower()
        format_values[format_extension] = format_uri_ref
    return format_values


def get_publisher_dict_from_dataset(publisher):
    if not publisher:
        return None, None
    if not isinstance(publisher, dict):
        publisher = json.loads(publisher)
    return publisher.get('url'), publisher.get('name')


def get_iana_media_type_values():
    media_type_values = {}
    file = os.path.join(__location__, 'iana_media_types.xml')
    tree = ET.parse(file)
    root = tree.getroot()
    registries = root.findall('.//ns:registry', media_types_namespaces)
    for registry in registries:
        registry_type = registry.get('id')
        records = registry.findall('.//ns:record', media_types_namespaces)
        for record in records:
            if record.find('ns:file', media_types_namespaces) is None:
                continue
            if record.find('ns:name', media_types_namespaces) is None:
                continue
            name = record.find('ns:name', media_types_namespaces).text.lower()
            file_value = record.find('ns:file', media_types_namespaces).text
            media_type_values[registry_type + '/' + name] = \
                media_types_namespaces['ns'] + '/' + file_value
    return media_type_values

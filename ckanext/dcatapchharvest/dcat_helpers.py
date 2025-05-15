import iribaker
import json
import os
from urlparse import urlparse
from ckantoolkit import config
from rdflib import URIRef, Graph
from rdflib.namespace import Namespace, RDF, SKOS
import xml.etree.ElementTree as ET
import logging

log = logging.getLogger(__name__)

DCT = Namespace("http://purl.org/dc/terms/")
EUTHEMES = \
    Namespace("http://publications.europa.eu/resource/authority/data-theme/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
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
  "foaf": FOAF,
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


def localize_by_language_priority(multilang_dict):
    for lang in get_langs():
        if multilang_dict.get(lang, ''):
            return multilang_dict[lang]
    return ''


def dataset_uri(dataset_dict, dataset_ref=None):
    """
    Returns a URI for the dataset

    This is a hack/workaround for the use case where data publishers create
    datsets on the test environment, export them to XML and then import them
    to the production site. In that case, the dataset uris will contain the
    url of the test environment, so we have to replace it with the prod one.
    """
    uri = (unicode(dataset_ref)
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
    return u'{0}/perma/{1}'.format(site_url, identifier)


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
    uri = (unicode(distribution)
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
    for prefix, namespace in frequency_namespaces.items():
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


class LicenseHandler:
    def __init__(self):
        self._license_cache = None

    def _bind_namespaces(self, graph):
        for prefix, namespace in license_namespaces.items():
            graph.bind(prefix, namespace)

    def _parse_graph(self, graph):
        file = os.path.join(__location__, 'license.ttl')
        graph.parse(file, format='turtle')

    def _get_license_homepage(self, graph, license_ref):
        for homepage in graph.objects(subject=license_ref,
                                      predicate=FOAF.homepage):
            return homepage
        return None

    def _get_license_literal(self, graph, license_ref):
        for license_pref_label in graph.objects(subject=license_ref,
                                                predicate=SKOSXL.prefLabel):
            try:
                return next(graph.objects(subject=license_pref_label,
                                          predicate=SKOSXL.literalForm))
            except StopIteration:
                continue
        return None

    def _process_graph(self, graph):
        license_ref_literal_mapping = {}
        license_homepages_literal_mapping = {}
        license_homepage_ref_mapping = {}

        for ogdch_license_ref in graph.subjects(predicate=RDF.type,
                                                object=SKOS.Concept):
            license_homepage = self._get_license_homepage(graph,
                                                          ogdch_license_ref)
            license_literal = self._get_license_literal(graph,
                                                        ogdch_license_ref)

            license_homepages_literal_mapping[unicode(license_homepage)] = \
                unicode(license_literal)
            license_ref_literal_mapping[unicode(ogdch_license_ref)] = \
                unicode(license_literal)
            license_homepage_ref_mapping[unicode(license_homepage)] = \
                unicode(ogdch_license_ref)

        return (license_homepages_literal_mapping,
                license_ref_literal_mapping, license_homepage_ref_mapping)

    def _get_license_values(self):
        if self._license_cache is None:
            try:
                g = Graph()
                self._bind_namespaces(g)
                self._parse_graph(g)

                (license_homepages_literal_mapping,
                 license_ref_literal_mapping,
                 license_homepage_ref_mapping) = self._process_graph(g)

                self._license_cache = (license_homepages_literal_mapping,
                                       license_ref_literal_mapping,
                                       license_homepage_ref_mapping)
            except Exception as e:
                raise RuntimeError("Failed to load license values: %s"
                                   % e)
        return self._license_cache

    def get_license_ref_uri_by_name(self, vocabulary_name):
        _, license_ref_literal_vocabulary, _ = self._get_license_values()
        return next((key for key, value in
                     license_ref_literal_vocabulary.items()
                     if unicode(vocabulary_name) == value),
                    None)

    def get_license_ref_uri_by_homepage_uri(self, vocabulary_name):
        _, _, license_homepage_ref_vocabulary = self._get_license_values()
        return license_homepage_ref_vocabulary.get(unicode(vocabulary_name))

    def get_license_name_by_ref_uri(self, vocabulary_uri):
        _, license_ref_literal_vocabulary, _ = self._get_license_values()
        return license_ref_literal_vocabulary.get(
            unicode(vocabulary_uri))

    def get_license_name_by_homepage_uri(self, vocabulary_uri):
        license_homepages_literal_vocabulary, _, _ = self._get_license_values()
        return license_homepages_literal_vocabulary.get(
            unicode(vocabulary_uri))

    def get_license_homepage_uri_by_name(self, vocabulary_name):
        license_homepages_literal_vocabulary, _, _ = self._get_license_values()
        return next((key for key, value in
                     license_homepages_literal_vocabulary.items()
                     if unicode(vocabulary_name) == value),
                    None)

    def get_license_homepage_uri_by_uri(self, vocabulary_uri):
        _, _, license_homepage_ref_vocabulary = self._get_license_values()
        license_homepages = list(license_homepage_ref_vocabulary.keys())
        if unicode(vocabulary_uri) in license_homepages:
            return unicode(vocabulary_uri)
        return next((key for key, value in
                     license_homepage_ref_vocabulary.items()
                     if unicode(vocabulary_uri) == value),
                    None)


def get_theme_mapping():
    g = Graph()
    theme_mapping = {}
    for prefix, namespace in theme_namespaces.items():
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
                pagination[key] = unicode(obj)
    return pagination


def get_format_values():
    """Generate a dict that maps our standardised formats (the keys in this file
    https://github.com/opendata-swiss/ckanext-switzerland-ng/blob/master/ckanext/switzerland/helpers/format_mapping.yaml)
    to the URIs in the EU file-type vocabulary
    (http://publications.europa.eu/resource/authority/file-type).

    The standardised formats are converted to lowercase, with non-letter
    characters replaced by '_', for use as keys in this dict.
    """
    g = Graph()
    for prefix, namespace in format_namespaces.items():
        g.bind(prefix, namespace)
    formats_file = os.path.join(__location__, 'formats.xml')
    g.parse(formats_file, format='xml')
    format_values = {}
    for format_uri_ref in g.subjects():
        format_extension = format_uri_ref.split('/')[-1].lower()
        format_values[format_extension] = format_uri_ref

    # Add special cases that aren't so easy to map.
    format_values.update(
        {
            "api": "http://publications.europa.eu/resource/authority/file-type/REST",  # noqa
            "esri_ascii_grid": "http://publications.europa.eu/resource/authority/file-type/GRID_ASCII",  # noqa
            "sparql": "http://publications.europa.eu/resource/authority/file-type/SPARQLQ",  # noqa
            "wcs": "http://publications.europa.eu/resource/authority/file-type/WCS_SRVC",  # noqa
            "wfs": "http://publications.europa.eu/resource/authority/file-type/WFS_SRVC",  # noqa
            "wms": "http://publications.europa.eu/resource/authority/file-type/WMS_SRVC",  # noqa
            "wmts": "http://publications.europa.eu/resource/authority/file-type/WMTS_SRVC",  # noqa
            "worldfile": "http://publications.europa.eu/resource/authority/file-type/WORLD"  # noqa
        }
    )

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
            name = record.find(
                'ns:name', media_types_namespaces
            ).text.lower()

            if record.find('ns:file', media_types_namespaces) is not None:
                uri_suffix = record.find(
                    'ns:file', media_types_namespaces
                ).text
            else:
                uri_suffix = registry_type + '/' + name

            media_type_values[registry_type + '/' + name] = \
                media_types_namespaces['ns'] + '/media-types/' + uri_suffix

    return media_type_values


def get_language_uri_map():
    """
    Parses language.xml and builds a mapping:
    { 'de': 'http://publications.europa.eu/resource/authority/language/DEU',
    'en': 'http://publications.europa.eu/resource/authority/language/ENG',
    ...}
    """
    xml_file = os.path.join(__location__, 'language.xml')
    tree = ET.parse(xml_file)
    root = tree.getroot()

    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'skos': 'http://www.w3.org/2004/02/skos/core#'
    }

    lang_map = {}

    for desc in root.findall('.//rdf:Description', ns):
        uri = desc.attrib.get('{{{}}}about'.format(ns["rdf"]))
        notation = desc.find('skos:notation', ns)
        if uri and notation is not None:
            lang_code = notation.text.strip().lower()
            lang_map[lang_code] = uri

    return lang_map

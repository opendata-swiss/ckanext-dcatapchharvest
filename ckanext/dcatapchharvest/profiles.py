import json
import logging
import re
from datetime import datetime, timedelta

from ckan.lib.munge import munge_tag
from ckantoolkit import config
import isodate
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, Namespace

import ckanext.dcatapchharvest.dcat_helpers as dh
from ckanext.dcat.profiles import CleanedURIRef, RDFProfile, SchemaOrgProfile

log = logging.getLogger(__name__)

valid_frequencies = dh.get_frequency_values()
valid_licenses = dh.get_license_values()
eu_theme_mapping = dh.get_theme_mapping()
valid_formats = dh.get_format_values()
valid_media_types = dh.get_iana_media_type_values()


DCT = dh.DCT
DCAT = Namespace('http://www.w3.org/ns/dcat#')
VCARD = Namespace('http://www.w3.org/2006/vcard/ns#')
SCHEMA = Namespace('http://schema.org/')
ADMS = Namespace('http://www.w3.org/ns/adms#')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
TIME = Namespace('http://www.w3.org/2006/time')
LOCN = Namespace('http://www.w3.org/ns/locn#')
GSP = Namespace('http://www.opengis.net/ont/geosparql#')
OWL = Namespace('http://www.w3.org/2002/07/owl#')
SPDX = Namespace('http://spdx.org/rdf/terms#')
XSD = Namespace('http://www.w3.org/2001/XMLSchema#')
EUTHEMES = dh.EUTHEMES
ODRS = Namespace('http://schema.theodi.org/odrs#')

GEOJSON_IMT = 'https://www.iana.org/assignments/media-types/application/vnd.geo+json'  # noqa

EMAIL_MAILTO_PREFIX = 'mailto:'
ORGANIZATION_BASE_URL = 'https://opendata.swiss/organization/'

DATE_FORMAT = "%Y-%m-%d"
YEAR_MONTH_FORMAT = "%Y-%m"
YEAR_FORMAT = "%Y"

namespaces = {
    'dct': DCT,
    'dcat': DCAT,
    'adms': ADMS,
    'vcard': VCARD,
    'foaf': FOAF,
    'schema': SCHEMA,
    'time': TIME,
    'skos': SKOS,
    'locn': LOCN,
    'gsp': GSP,
    'owl': OWL,
    'xsd': XSD,
    'euthemes': EUTHEMES,
    'odrs': ODRS,
}

OGD_THEMES_URI = 'http://opendata.swiss/themes/'
CHTHEMES_URI = 'http://dcat-ap.ch/vocabulary/themes/'
EUTHEMES_URI = 'http://publications.europa.eu/resource/authority/data-theme/'

slug_id_pattern = re.compile('[^/]+(?=/$|$)')


class MultiLangProfile(RDFProfile):
    def _add_multilang_value(self, subject, predicate, dataset_key=None,
                             dataset_dict=None,
                             multilang_values=None):  # noqa
        if not multilang_values and dataset_dict and dataset_key:
            multilang_values = dataset_dict.get(dataset_key)
        if multilang_values:
            try:
                for key, values in multilang_values.items():
                    if values:
                        # the values can be either a multilang-dict or they are
                        # nested in another iterable (e.g. keywords)
                        if not hasattr(values, '__iter__'):
                            values = [values]
                        for value in values:
                            if value:
                                self.g.add((subject, predicate, Literal(value, lang=key)))  # noqa
            # if multilang_values is not iterable, it is simply added as a non-
            # translated Literal
            except AttributeError:
                self.g.add((subject, predicate, Literal(multilang_values)))

    def _add_multilang_triples_from_dict(self, _dict, subject, items):
        for item in items:
            key, predicate, fallbacks, _type = item
            self._add_multilang_triple_from_dict(
                _dict,
                subject,
                predicate,
                key,
                fallbacks=fallbacks
            )

    def _add_multilang_triple_from_dict(self, _dict, subject, predicate, key, fallbacks=None):  # noqa
        '''
        Adds a new multilang triple to the graph with the provided parameters

        The subject and predicate of the triple are passed as the relevant
        RDFLib objects (URIRef or BNode). The object is always a literal value,
        which is extracted from the dict using the provided key (see
        `_get_dict_value`).
        '''
        value = self._get_dict_value(_dict, key)

        if value:
            self._add_multilang_value(
                subject,
                predicate,
                multilang_values=value
            )


class SwissDCATAPProfile(MultiLangProfile):
    '''
    An RDF profile for the DCAT-AP Switzerland recommendation for data portals

    It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def _object_value(self, subject, predicate, multilang=False):
        '''
        Given a subject and a predicate, returns the value of the object

        Both subject and predicate must be rdflib URIRef or BNode objects

        If found, the unicode representation is returned, else None
        '''
        default_lang = 'de'
        lang_dict = {}
        for o in self.g.objects(subject, predicate):
            if multilang and o.language:
                lang_dict[o.language] = str(o)
            elif multilang:
                lang_dict[default_lang] = str(o)
            else:
                return str(o)
        if multilang:
            # when translation does not exist, create an empty one
            for lang in dh.get_langs():
                if lang not in lang_dict:
                    lang_dict[lang] = ''
        return lang_dict

    def _object_value_and_datatype(self, subject, predicate):
        """Given a subject and a predicate, returns the unicode representation
        of the object and its datatype, if the object is an rdflib Literal.

        If the object is not a Literal, the datatype returned is None.
        """
        for o in self.g.objects(subject, predicate):
            if isinstance(o, Literal):
                return str(o), o.datatype
            return str(o), None
        return None, None

    def _get_publisher_url_from_identifier(self, identifier):
        identifier_split = identifier.split('@')
        if len(identifier_split) > 1:
            return ORGANIZATION_BASE_URL + identifier_split[1]
        return ''

    def _publisher(self, subject, identifier):
        """
        Returns a dict with details about a dct:publisher entity, a foaf:Agent

        Both subject and predicate must be rdflib URIRef or BNode objects

        Examples:

        <dct:publisher>
            <foaf:Organization rdf:about="http://orgs.vocab.org/some-org">
                <foaf:name>Publishing Organization for dataset 1</foaf:name>
            </foaf:Organization>
        </dct:publisher>

        {
            'url': 'http://orgs.vocab.org/some-org',
            'name': 'Publishing Organization for dataset 1',
        }

        Returns keys for url, name with the values set to
        an empty string if they could not be found
        """
        publisher = {}
        for agent in self.g.objects(subject, DCT.publisher):
            publisher['url'] = (str(agent) if isinstance(agent,
                                URIRef) else '')
            publisher_name = self._object_value(agent, FOAF.name)
            publisher_deprecated = self._object_value(agent, RDFS.label)
            if publisher_name:
                publisher['name'] = publisher_name
            elif publisher_deprecated:
                publisher['name'] = publisher_deprecated
            else:
                publisher['name'] = ''

        if not publisher.get('url'):
            publisher['url'] = self._get_publisher_url_from_identifier(
                identifier
            )
        return json.dumps(publisher)

    def _relations(self, subject):

        relations = []

        for relation_node in self.g.objects(subject, DCT.relation):
            relation = {
                'label': self._object_value(relation_node, RDFS.label),
                'url': relation_node
            }
            relations.append(relation)

        return relations

    def _qualified_relations(self, subject):
        qualified_relations = []

        for relation_node in self.g.objects(subject, DCAT.qualifiedRelation):
            qualified_relations.append({
                "relation": self._object_value(relation_node, DCT.relation),
                "had_role": self._object_value(relation_node, DCAT.hadRole),
            })

        return qualified_relations

    def _get_eu_or_iana_format(self, subject):
        format_value = self._object_value(subject, DCT['format'])
        if isinstance(format_value, dict):
            log.debug("The format object is a dictionary type.")
        else:
            lowercase_format_value = format_value.lower().split('/')[-1]
            if lowercase_format_value in valid_formats \
                    or lowercase_format_value in valid_media_types:
                return lowercase_format_value
            else:
                return ''

    def _get_iana_media_type(self, subject):
        media_type_value_raw = self._object_value(subject, DCAT.mediaType)
        if isinstance(media_type_value_raw, dict):
            log.debug("The media type object is a dictionary type.")
        else:
            # This matches either a URI (http://example.com/foo/bar) or
            # a string (foo/bar)
            pattern = r'(.*\/|^)(.+\/.+)$'
            media_type_value_re = re.search(pattern, media_type_value_raw)
            if media_type_value_re:
                media_type_value = media_type_value_re.group(2)
            else:
                media_type_value = media_type_value_raw

            lowercase_media_type_value = media_type_value.lower()
            if lowercase_media_type_value in valid_media_types:
                return lowercase_media_type_value
            else:
                return ''

    def _license_rights_name(self, subject, predicate):
        for node in self.g.objects(subject, predicate):
            # DCAT-AP CH v1: the license as a literal (should be
            # the code for one of the DCAT-AP CH licenses)
            if isinstance(node, Literal):
                return str(node)
            if isinstance(node, URIRef):
                return dh.get_license_name_by_uri(node)
        return None

    def _license_rights_uri(self, subject, predicate):
        for node in self.g.objects(subject, predicate):
            # DCAT-AP CH v2 compatible license has to be a URI.
            if isinstance(node, Literal):
                return dh.get_license_uri_by_name(node)
            if isinstance(node, URIRef):
                return node
        return None

    def _keywords(self, subject):
        keywords = {}
        # initialize the keywords with empty lists for all languages
        for lang in dh.get_langs():
            keywords[lang] = []

        for keyword_node in self.g.objects(subject, DCAT.keyword):
            lang = keyword_node.language
            keyword = munge_tag(str(keyword_node))
            keywords.setdefault(lang, []).append(keyword)

        return keywords

    def _contact_points(self, subject):

        contact_points = []

        for contact_node in self.g.objects(subject, DCAT.contactPoint):
            email = self._object_value(contact_node, VCARD.hasEmail)
            if email:
                email_clean = email.replace(EMAIL_MAILTO_PREFIX, '')
            else:
                email_clean = ''
            contact = {
                'name': self._object_value(contact_node, VCARD.fn),
                'email': email_clean
            }

            contact_points.append(contact)

        return contact_points

    def _temporals(self, subject):

        temporals = []

        for temporal_node in self.g.objects(subject, DCT.temporal):
            # Currently specified properties in DCAT-AP.
            start_date, start_date_type = self._object_value_and_datatype(
                temporal_node, DCAT.startDate)
            end_date, end_date_type = self._object_value_and_datatype(
                temporal_node, DCAT.endDate)
            if not start_date or not end_date:
                # Previously specified properties in DCAT-AP. Should still be
                # accepted.
                start_date, start_date_type = self._object_value_and_datatype(
                    temporal_node, SCHEMA.startDate)
                end_date, end_date_type = self._object_value_and_datatype(
                    temporal_node, SCHEMA.endDate)
            if not start_date or not end_date:
                continue

            cleaned_start_date = self._clean_datetime(
                start_date, start_date_type)
            cleaned_end_date = self._clean_end_datetime(
                end_date, end_date_type)
            if not cleaned_start_date or not cleaned_end_date:
                continue
            temporals.append({
                'start_date': cleaned_start_date,
                'end_date': cleaned_end_date,
            })

        return temporals

    def _clean_datetime(self, datetime_value, data_type):
        """Convert a literal in one of the accepted data types into an
        isoformat datetime string.

        Accepted types are: xsd:date, xsd:dateTime, xsd:gYear, or
        xsd:gYearMonth; or schema:Date or schema:DateTime, for temporals
        specified as schema:startDate and schema:endDate.

        We only consider parts of the date that are expected from the given
        data_type, e.g. the year of an xsd:gYear, even if the month and day
        have been included in the datetime_value. If a datetime_value with
        data_type of xsd:dateTime or schema:DateTime does not contain time
        information, we discard it.
        """
        try:
            if data_type == XSD.dateTime or data_type == SCHEMA.DateTime:
                dt = isodate.parse_datetime(datetime_value)

                return dt.isoformat()
            elif data_type == XSD.date or data_type == SCHEMA.Date:
                dt = datetime.strptime(datetime_value, DATE_FORMAT)

                return dt.isoformat()
            elif data_type == XSD.gYearMonth:
                datetime_value = datetime_value[:len('YYYY-MM')]
                dt = datetime.strptime(datetime_value, YEAR_MONTH_FORMAT)

                return dt.isoformat()
            elif data_type == XSD.gYear:
                datetime_value = datetime_value[:len('YYYY')]
                dt = datetime.strptime(datetime_value, YEAR_FORMAT)

                return dt.isoformat()
        except ValueError:
            return None

    def _clean_end_datetime(self, datetime_value, data_type):
        """Convert a literal in one of the accepted types into the latest
        possible date for that value, and then return it as an isoformat
        datetime string.

        E.g. if the datetime_value has a xsd:gYear type, return the isoformat
        datetime string for the end of that year.

        Accepted types are: xsd:date, xsd:dateTime, xsd:gYear, or
        xsd:gYearMonth; or schema:Date or schema:DateTime, for temporals
        specified as schema:startDate and schema:endDate.

        We only consider the parts of the date that are expected from the given
        data_type, e.g. the year of an xsd:gYear, even if the month and day
        have been included in the datetime_value. If a datetime_value with
        data_type of xsd:dateTime or schema:DateTime does not contain time
        information, we discard it.
        """
        try:
            if data_type == XSD.dateTime or data_type == SCHEMA.DateTime:
                dt = isodate.parse_datetime(datetime_value)

                return dt.isoformat()
            elif data_type == XSD.date or data_type == SCHEMA.Date:
                dt = datetime.strptime(datetime_value, DATE_FORMAT)
                end_datetime = datetime.max.replace(
                    year=dt.year, month=dt.month, day=dt.day)

                return end_datetime.isoformat()
            elif data_type == XSD.gYearMonth:
                datetime_value = datetime_value[:len('YYYY-MM')]
                dt = datetime.strptime(datetime_value, YEAR_MONTH_FORMAT)
                # We need to calculate the last day of the month, which varies.
                d = dt.replace(month=dt.month + 1) + timedelta(days=-1)

                end_datetime = datetime.max.replace(
                    year=d.year, month=d.month, day=d.day)

                return end_datetime.isoformat()
            elif data_type == XSD.gYear:
                datetime_value = datetime_value[:len('YYYY')]
                dt = datetime.strptime(datetime_value, YEAR_FORMAT)
                end_datetime = datetime.max.replace(year=dt.year)

                return end_datetime.isoformat()
        except ValueError:
            return None

    def _get_eu_accrual_periodicity(self, subject):
        ogdch_value = self._object_value(subject, DCT.accrualPeriodicity)
        ogdch_value = URIRef(ogdch_value)
        for key, value in list(valid_frequencies.items()):
            if ogdch_value == value:
                ogdch_value = key
                return ogdch_value
            elif ogdch_value == key:
                log.info("EU frequencies are already used.")
                return ogdch_value

        log.info("There is no such frequency as '%s' "
                 "in the official list of frequencies" % ogdch_value)
        return ""

    def _get_groups(self, subject):
        """Map the DCAT.theme values of a dataset to themes from the EU theme
        vocabulary http://publications.europa.eu/resource/authority/data-theme
        """
        group_names = []
        dcat_theme_urls = self._object_value_list(subject, DCAT.theme)

        if dcat_theme_urls:
            for dcat_theme_url in dcat_theme_urls:
                eu_theme_url = None

                # Python 2 / 3 compatibility
                import sys
                if sys.version_info[0] >= 3:
                    unicode = str

                # Case 1: We get a deprecated opendata.swiss theme. Replace
                #         the base url with the dcat-ap.ch base url, so we can
                #         look it up in the theme mapping.
                if dcat_theme_url.startswith(OGD_THEMES_URI):
                    new_theme_url = dcat_theme_url.replace(
                        OGD_THEMES_URI, CHTHEMES_URI)

                    eu_theme_url = unicode(
                        eu_theme_mapping[URIRef(new_theme_url)][0])

                # Case 2: We get a dcat-ap.ch theme (the same as the
                #         opendata.swiss themes, but different base url). Get
                #         the correct EU theme from the theme mapping.
                elif dcat_theme_url.startswith(CHTHEMES_URI):
                    eu_theme_url = unicode(
                        eu_theme_mapping[URIRef(dcat_theme_url)][0])

                # Case 3: We get an EU theme and don't need to look it up in
                #         the mapping.
                elif dcat_theme_url.startswith(EUTHEMES_URI):
                    eu_theme_url = dcat_theme_url

                if eu_theme_url is None:
                    log.info("Could not find an EU theme that matched the "
                             "given theme: {}".format(dcat_theme_url))
                    continue

                search_result = slug_id_pattern.search(eu_theme_url)
                eu_theme_slug = search_result.group().lower()
                group_names.append(eu_theme_slug)

        # Deduplicate group names before returning list of group dicts
        return [{'name': name} for name in list(set(group_names))]

    def parse_dataset(self, dataset_dict, dataset_ref):  # noqa
        log.debug("Parsing dataset '%r'" % dataset_ref)

        dataset_dict['temporals'] = []
        dataset_dict['tags'] = []
        dataset_dict['extras'] = []
        dataset_dict['resources'] = []
        dataset_dict['relations'] = []
        dataset_dict['see_alsos'] = []
        dataset_dict['qualified_relations'] = []

        # Basic fields
        for key, predicate in (
                ('identifier', DCT.identifier),
                ('spatial_uri', DCT.spatial),
                ('spatial', DCT.spatial),
                ('url', DCAT.landingPage),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        # Accrual periodicity
        dataset_dict['accrual_periodicity'] = self._get_eu_accrual_periodicity(
            dataset_ref
        )

        # Timestamp fields
        for key, predicate in (
                ('issued', DCT.issued),
                ('modified', DCT.modified),
        ):
            value, datatype = self._object_value_and_datatype(
                dataset_ref, predicate)
            if value:
                cleaned_value = self._clean_datetime(value, datatype)
                if cleaned_value:
                    dataset_dict[key] = cleaned_value

        # Multilingual basic fields
        for key, predicate in (
                ('title', DCT.title),
                ('description', DCT.description),
        ):
            value = self._object_value(dataset_ref, predicate, multilang=True)
            if value:
                dataset_dict[key] = value

        # Tags
        keywords = self._object_value_list(dataset_ref, DCAT.keyword) or []
        for keyword in keywords:
            dataset_dict['tags'].append({'name': munge_tag(str(keyword))})

        # Keywords
        dataset_dict['keywords'] = self._keywords(dataset_ref)

        # Themes
        dataset_dict['groups'] = self._get_groups(dataset_ref)

        #  Languages
        languages = self._object_value_list(dataset_ref, DCT.language)
        if languages:
            dataset_dict['language'] = languages

        # Contact details
        dataset_dict['contact_points'] = self._contact_points(
            dataset_ref,
        )

        # Publisher
        dataset_dict['publisher'] = self._publisher(
            dataset_ref,
            dataset_dict.get('identifier', '')
        )

        # Relations
        dataset_dict['relations'] = self._relations(dataset_ref)
        for relation in dataset_dict['relations']:
            if relation['label'] == {}:
                relation['label'] = str(relation.get('url', ''))

        # Temporal
        dataset_dict['temporals'] = self._temporals(dataset_ref)

        # References
        see_alsos = self._object_value_list(dataset_ref, RDFS.seeAlso)
        for see_also in see_alsos:
            dataset_dict['see_alsos'].append({'dataset_identifier': see_also})

        dataset_dict["qualified_relations"] = self._qualified_relations(
            dataset_ref
        )

        # Dataset URI
        dataset_uri = dh.dataset_uri(dataset_dict, dataset_ref)
        dataset_dict['extras'].append({'key': 'uri', 'value': dataset_uri})

        # Documentation
        dataset_dict['documentation'] = self._object_value_list(
            dataset_ref, FOAF.page
        )

        # Conformance
        dataset_dict['conforms_to'] = self._object_value_list(
            dataset_ref, DCT.conformsTo
        )

        # Resources
        for distribution in self._distributions(dataset_ref):
            resource_dict = {
                'media_type': '',
                'language': [],
            }

            #  Simple values
            for key, predicate in (
                    ('identifier', DCT.identifier),
                    ('download_url', DCAT.downloadURL),
                    ('url', DCAT.accessURL),
                    ('coverage', DCT.coverage),
            ):
                value = self._object_value(distribution, predicate)
                if value:
                    resource_dict[key] = value

            #  Rights & License save name
            rights = self._license_rights_name(distribution, DCT.rights)
            license = self._license_rights_name(distribution, DCT.license)
            if rights is None and license is not None:
                resource_dict['license'] = license
                resource_dict['rights'] = license
            if rights is not None and license is None:
                resource_dict['license'] = rights
                resource_dict['rights'] = rights
            if license is not None and rights is not None:
                resource_dict['license'] = license
                resource_dict['rights'] = rights
                if 'cc' in rights:
                    resource_dict['license'] = rights
                    resource_dict['rights'] = license

            # Format & Media type
            resource_dict['format'] = \
                self._get_eu_or_iana_format(distribution)
            resource_dict['media_type'] = \
                self._get_iana_media_type(distribution)
            # Set 'media_type' as 'format'
            # if 'media_type' is not set but 'format' exists
            if not resource_dict.get('media_type') \
                    and resource_dict.get('format'):
                resource_dict['media_type'] = resource_dict['format']
            # Set 'format' as 'media_type'
            # if 'format' is not set but 'media_type' exists
            elif not resource_dict.get('format') \
                    and resource_dict.get('media_type'):
                resource_dict['format'] = resource_dict['media_type']

            # Documentation
            resource_dict['documentation'] = self._object_value_list(
                distribution, FOAF.page
            )

            # Access services
            resource_dict['access_services'] = self._object_value_list(
                distribution, DCAT.accessService
            )

            # Temporal resolution
            resource_dict['temporal_resolution'] = self._object_value(
                distribution, DCAT.temporalResolution
            )

            # Timestamp fields
            for key, predicate in (
                    ('issued', DCT.issued),
                    ('modified', DCT.modified),
            ):
                value, datatype = self._object_value_and_datatype(
                    distribution, predicate)
                if value:
                    cleaned_value = self._clean_datetime(value, datatype)
                    if cleaned_value:
                        resource_dict[key] = cleaned_value

            # Multilingual fields
            for key, predicate in (
                    ('title', DCT.title),
                    ('description', DCT.description),
            ):
                value = self._object_value(
                    distribution,
                    predicate,
                    multilang=True)
                if value:
                    resource_dict[key] = value

            resource_dict['url'] = (self._object_value(distribution,
                                                       DCAT.accessURL) or
                                    self._object_value(distribution,
                                                       DCAT.downloadURL) or '')

            # languages
            for language in self._object_value_list(
                    distribution,
                    DCT.language
            ):
                resource_dict['language'].append(language)

            # byteSize
            byte_size = self._object_value_int(distribution, DCAT.byteSize)
            if byte_size is not None:
                resource_dict['byte_size'] = byte_size

            # Distribution URI (explicitly show the missing ones)
            resource_dict['uri'] = dh.resource_uri(
                resource_dict, distribution)

            dataset_dict['resources'].append(resource_dict)

        log.debug("Parsed dataset '%r': %s" % (dataset_ref, dataset_dict))

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):  # noqa

        log.debug("Create graph from dataset '%s'" % dataset_dict['name'])

        dataset_uri = dh.dataset_uri(dataset_dict, dataset_ref)
        dataset_ref = URIRef(dataset_uri)

        g = self.g

        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        g.add((dataset_ref, RDF.type, DCAT.Dataset))

        # Basic fields
        items = [
            ('identifier', DCT.identifier, ['guid', 'id'], Literal),
            ('version', OWL.versionInfo, ['dcat_version'], Literal),
            ('version_notes', ADMS.versionNotes, None, Literal),
            ('frequency', DCT.accrualPeriodicity, None, Literal),
            ('access_rights', DCT.accessRights, None, Literal),
            ('dcat_type', DCT.type, None, Literal),
            ('provenance', DCT.provenance, None, Literal),
            ('spatial', DCT.spatial, None, Literal),
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, items)

        self._add_multilang_value(
            dataset_ref,
            DCT.description,
            'description',
            dataset_dict
        )
        self._add_multilang_value(
            dataset_ref,
            DCT.title,
            'title',
            dataset_dict
        )

        # LandingPage
        landing_page_url = dataset_dict.get('url')
        if landing_page_url:
            try:
                landing_page = dh.uri_to_iri(landing_page_url)
            except ValueError:
                pass
            else:
                g.add((dataset_ref, DCAT.landingPage, URIRef(landing_page)))

        # Keywords
        self._add_multilang_value(
            dataset_ref,
            DCAT.keyword,
            'keywords',
            dataset_dict
        )

        # Dates
        items = [
            ('issued', DCT.issued, None, Literal),
            ('modified', DCT.modified, None, Literal),
        ]
        self._add_date_triples_from_dict(dataset_dict, dataset_ref, items)

        # Update Interval
        accrual_periodicity = dataset_dict.get('accrual_periodicity')
        if accrual_periodicity:
            self._accrual_periodicity_to_graph(dataset_ref,
                                               accrual_periodicity)

        # Lists
        items = [
            ('language', DCT.language, None, Literal),
            ('theme', DCAT.theme, None, URIRef),
            ('alternate_identifier', ADMS.identifier, None, Literal),
            ('has_version', DCT.hasVersion, None, Literal),
            ('is_version_of', DCT.isVersionOf, None, Literal),
            ('source', DCT.source, None, Literal),
            ('sample', ADMS.sample, None, Literal),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

        # Relations
        if dataset_dict.get('relations'):
            relations = dataset_dict.get('relations')
            for relation in relations:
                relation_name = relation['label']
                try:
                    relation_url = dh.uri_to_iri(relation['url'])
                except ValueError:
                    # skip this relation if the URL is invalid
                    continue

                relation = URIRef(relation_url)
                g.add((relation, RDFS.label, Literal(relation_name)))
                g.add((dataset_ref, DCT.relation, relation))

        # References
        if dataset_dict.get('see_alsos'):
            references = dataset_dict.get('see_alsos')
            for reference in references:
                # we only expect dicts here
                if not isinstance(reference, dict):
                    continue
                reference_identifier = reference.get('dataset_identifier')
                if reference_identifier:
                    g.add((
                        dataset_ref,
                        RDFS.seeAlso,
                        Literal(reference_identifier)
                    ))

        if dataset_dict.get("qualified_relations"):
            for reference in dataset_dict["qualified_relations"]:
                if not reference.get("relation"):
                    continue

                qualified_relation = BNode()
                g.add((qualified_relation, RDF.type, DCAT.Relationship))
                g.add((
                    qualified_relation,
                    DCT.relation,
                    URIRef(reference["relation"])
                ))

                if reference.get("had_role"):
                    g.add((
                        qualified_relation,
                        DCAT.hadRole,
                        URIRef(reference["had_role"])
                    ))

                g.add((
                    dataset_ref,
                    DCAT.qualifiedRelation,
                    qualified_relation
                ))

        # Contact details
        if dataset_dict.get('contact_points'):
            contact_points = self._get_dataset_value(dataset_dict, 'contact_points')  # noqa
            for contact_point in contact_points:
                contact_details = BNode()
                contact_point_email = \
                    EMAIL_MAILTO_PREFIX + contact_point['email']
                contact_point_name = contact_point['name']

                g.add((contact_details, RDF.type, VCARD.Organization))
                g.add((contact_details, VCARD.hasEmail, URIRef(contact_point_email)))  # noqa
                g.add((contact_details, VCARD.fn, Literal(contact_point_name)))

                g.add((dataset_ref, DCAT.contactPoint, contact_details))

        # Publisher
        self._publisher_to_graph(dataset_ref,
                                 dataset_dict)

        # Temporals
        temporals = dataset_dict.get('temporals')
        if temporals:
            for temporal in temporals:
                start = temporal['start_date']
                end = temporal['end_date']
                if start or end:
                    temporal_extent = BNode()
                    g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
                    if start:
                        self._add_date_triple(
                            temporal_extent,
                            DCAT.startDate,
                            start
                        )
                    if end:
                        self._add_date_triple(
                            temporal_extent,
                            DCAT.endDate,
                            end
                        )
                    g.add((dataset_ref, DCT.temporal, temporal_extent))

        # Documentation
        documentation = dataset_dict.get('documentation', [])
        for link in documentation:
            doc = URIRef(link)
            g.add((doc, RDF.type, FOAF.Document))
            g.add((dataset_ref, FOAF.page, doc))

        # Conformance
        conformance_uris = dataset_dict.get('conforms_to', [])
        for uri in conformance_uris:
            ref = URIRef(uri)
            g.add((dataset_ref, DCT.conformsTo, ref))

        # Themes
        groups = self._get_dataset_value(dataset_dict, 'groups', [])
        for group_name in groups:
            eu_theme_ref = URIRef(EUTHEMES_URI + group_name.get('name'))
            g.add((
                dataset_ref,
                DCAT.theme,
                eu_theme_ref,
            ))

        # Resources
        for resource_dict in dataset_dict.get('resources', []):
            distribution = URIRef(dh.resource_uri(resource_dict))

            g.add((dataset_ref, DCAT.distribution, distribution))
            g.add((distribution, RDF.type, DCAT.Distribution))

            #  Simple values
            items = [
                ('status', ADMS.status, None, Literal),
                ('coverage', DCT.coverage, None, Literal),
                ('identifier', DCT.identifier, None, Literal),
                ('spatial', DCT.spatial, None, Literal),
            ]

            self._rights_and_license_to_graph(resource_dict, distribution)
            self._format_and_media_type_to_graph(resource_dict, distribution)

            self._add_triples_from_dict(resource_dict, distribution, items)
            self._add_multilang_value(distribution, DCT.title, 'display_name', resource_dict)  # noqa
            self._add_multilang_value(distribution, DCT.description, 'description', resource_dict)  # noqa

            #  Lists
            items = [
                ('language', DCT.language, None, Literal),
            ]
            self._add_list_triples_from_dict(resource_dict, distribution,
                                             items)

            # Download URL & Access URL
            download_url = resource_dict.get('download_url')
            if download_url:
                try:
                    download_url = dh.uri_to_iri(download_url)
                    g.add((
                        distribution,
                        DCAT.downloadURL,
                        URIRef(download_url)
                    ))
                except ValueError:
                    # only add valid URL
                    pass

            url = resource_dict.get('url')
            if (url and not download_url) or (url and url != download_url):
                try:
                    url = dh.uri_to_iri(url)
                    g.add((distribution, DCAT.accessURL, URIRef(url)))
                except ValueError:
                    # only add valid URL
                    pass
            elif download_url:
                g.add((distribution, DCAT.accessURL, URIRef(download_url)))

            # Documentation
            documentation = resource_dict.get('documentation', [])
            for link in documentation:
                doc = URIRef(link)
                g.add((doc, RDF.type, FOAF.Document))
                g.add((distribution, FOAF.page, doc))

            # Access Services
            access_services = resource_dict.get('access_services', [])
            for uri in access_services:
                ref = URIRef(uri)
                g.add((distribution, DCAT.accessService, ref))

            # Temporal Resolution
            if resource_dict.get('temporal_resolution'):
                g.add((
                    distribution,
                    DCAT.temporalResolution,
                    Literal(resource_dict['temporal_resolution'],
                            datatype=XSD.duration)
                ))

            # Dates
            items = [
                ('issued', DCT.issued, None, Literal),
                ('modified', DCT.modified, None, Literal),
            ]

            # ByteSize
            if resource_dict.get('byte_size'):
                g.add((distribution, DCAT.byteSize,
                       Literal(resource_dict['byte_size'])))

    def _rights_and_license_to_graph(self, resource_dict, distribution):
        g = self.g
        if resource_dict.get('rights'):
            rights_uri = dh.get_license_uri_by_name(
                resource_dict.get('rights')
            )
            if rights_uri is not None:
                rights_ref = URIRef(rights_uri)
                g.add((rights_ref, RDF.type, DCT.RightsStatement))
                g.add((distribution, DCT.rights, rights_ref))
            if rights_uri is None:
                rights_name = dh.get_license_name_by_uri(
                    resource_dict.get('rights')
                    )
                if rights_name is not None:
                    resource_rights_ref = URIRef(
                        resource_dict.get('rights')
                        )
                    g.add((
                        resource_rights_ref,
                        RDF.type,
                        DCT.RightsStatement)
                        )
                    g.add((distribution, DCT.rights, resource_rights_ref))

        if resource_dict.get('license'):
            license_uri = dh.get_license_uri_by_name(
                resource_dict.get('license')
            )
            if license_uri is not None:
                license_ref = URIRef(license_uri)
                g.add((license_ref, RDF.type, DCT.LicenseDocument))
                g.add((distribution, DCT.license, license_ref))
            if license_uri is None:
                license_name = dh.get_license_name_by_uri(
                    resource_dict.get('license')
                    )
                if license_name is not None:
                    resource_license_ref = URIRef(
                        resource_dict.get('license')
                        )
                    g.add((
                        resource_license_ref,
                        RDF.type,
                        DCT.LicenseDocument)
                        )
                    g.add(
                        (distribution, DCT.license, resource_license_ref)
                        )

    def _format_and_media_type_to_graph(self, resource_dict, distribution):
        g = self.g
        # Export format value if it matches EU vocabulary
        # Exception: if a format is not available in the EU vocabulary,
        # use IANA media type vocabulary
        if resource_dict.get('format'):
            lowercase_format_value = resource_dict.get('format').lower()
            if lowercase_format_value in valid_formats:
                g.add((
                    distribution,
                    DCT['format'],
                    URIRef(valid_formats[lowercase_format_value])
                ))
            elif lowercase_format_value not in valid_formats \
                    and lowercase_format_value in valid_media_types:
                g.add((
                    distribution,
                    DCT['format'],
                    URIRef(valid_media_types[lowercase_format_value])
                ))

        # Export media type if it matches IANA media type vocabulary
        if resource_dict.get('media_type'):
            media_type = resource_dict.get('media_type')
            if media_type in valid_media_types:
                g.add((
                    distribution,
                    DCAT.mediaType,
                    URIRef(valid_media_types[media_type])
                ))

    def graph_from_catalog(self, catalog_dict, catalog_ref):
        g = self.g
        g.add((catalog_ref, RDF.type, DCAT.Catalog))

    def _accrual_periodicity_to_graph(self, dataset_ref, accrual_periodicity):
        g = self.g
        old_valid_frequencies = [
            i for i in list(valid_frequencies.values())
            if i != URIRef(
                    "http://purl.org/cld/freq/completelyIrregular")
            ]
        if URIRef(accrual_periodicity) in \
                old_valid_frequencies + list(valid_frequencies.keys()):
            g.add((
                dataset_ref,
                DCT.accrualPeriodicity,
                URIRef(accrual_periodicity)
            ))

    def _publisher_to_graph(self, dataset_ref, dataset_dict):
        g = self.g
        publisher_uri, publisher_name = \
            dh.get_publisher_dict_from_dataset(
                dataset_dict.get('publisher')
            )
        if publisher_uri:
            publisher_ref = URIRef(publisher_uri)
        else:
            publisher_ref = BNode()
        g.add((publisher_ref, RDF.type, FOAF.Organization))
        if publisher_name:
            g.add((publisher_ref, FOAF.name, Literal(publisher_name)))
        g.add((dataset_ref, DCT.publisher, publisher_ref))


class SwissSchemaOrgProfile(SchemaOrgProfile, MultiLangProfile):
    def _basic_fields_graph(self, dataset_ref, dataset_dict):
        items = [
            ('identifier', SCHEMA.identifier, None, Literal),
            ('version', SCHEMA.version, ['dcat_version'], Literal),
            ('issued', SCHEMA.datePublished, None, Literal),
            ('modified', SCHEMA.dateModified, None, Literal),
            ('author', SCHEMA.author, ['contact_name', 'maintainer'], Literal),
            ('url', SCHEMA.sameAs, None, Literal),
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, items)

        items = [
            ('title', SCHEMA.name, None, Literal),
            ('description', SCHEMA.description, None, Literal),
        ]
        self._add_multilang_triples_from_dict(dataset_dict, dataset_ref, items)

    def _list_fields_graph(self, dataset_ref, dataset_dict):
        items = [
            ('language', SCHEMA.inLanguage, None, Literal),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

    def _publisher_graph(self, dataset_ref, dataset_dict):
        if any([
            self._get_dataset_value(dataset_dict, 'publisher_uri'),
            self._get_dataset_value(dataset_dict, 'publisher_name'),
            dataset_dict.get('organization'),
        ]):
            publisher_uri, publisher_name = \
                dh.get_publisher_dict_from_dataset(
                    dataset_dict.get('publisher')
                )
            if publisher_uri:
                publisher_details = CleanedURIRef(publisher_uri)
            else:
                publisher_details = BNode()

            self.g.add((publisher_details, RDF.type, SCHEMA.Organization))
            self.g.add((dataset_ref, SCHEMA.publisher, publisher_details))
            self.g.add((dataset_ref, SCHEMA.sourceOrganization, publisher_details))  # noqa

            if not publisher_name and dataset_dict.get('organization'):
                publisher_name = dataset_dict['organization']['title']
                self._add_multilang_value(
                    publisher_details,
                    SCHEMA.name,
                    multilang_values=publisher_name
                )
            else:
                self.g.add((publisher_details, SCHEMA.name, Literal(publisher_name)))  # noqa

            contact_point = BNode()
            self.g.add((publisher_details, SCHEMA.contactPoint, contact_point))

            self.g.add((contact_point, SCHEMA.contactType, Literal('customer service')))  # noqa

            publisher_url = self._get_dataset_value(dataset_dict, 'publisher_url')  # noqa
            if not publisher_url and dataset_dict.get('organization'):
                publisher_url = dataset_dict['organization'].get('url') or config.get('ckan.site_url', '')  # noqa

            self.g.add((contact_point, SCHEMA.url, Literal(publisher_url)))
            items = [
                ('publisher_email', SCHEMA.email, ['contact_email', 'maintainer_email', 'author_email'], Literal),  # noqa
                ('publisher_name', SCHEMA.name, ['contact_name', 'maintainer', 'author'], Literal),  # noqa
            ]

            self._add_triples_from_dict(dataset_dict, contact_point, items)

    def _temporal_graph(self, dataset_ref, dataset_dict):
        # schema.org temporalCoverage only allows to specify one temporal
        # DCAT-AP Switzerland allows to specify multiple
        # for the mapping we always use the first one
        temporals = self._get_dataset_value(dataset_dict, 'temporals')
        try:
            start = temporals[0].get('start_date')
            end = temporals[0].get('end_date')
        except (IndexError, KeyError, TypeError):
            # do not add temporals if there are none
            return
        if start or end:
            if start and end:
                self.g.add((dataset_ref, SCHEMA.temporalCoverage, Literal('%s/%s' % (start, end))))  # noqa
            elif start:
                self._add_date_triple(dataset_ref, SCHEMA.temporalCoverage, start)  # noqa
            elif end:
                self._add_date_triple(dataset_ref, SCHEMA.temporalCoverage, end)  # noqa

    def _tags_graph(self, dataset_ref, dataset_dict):
        for tag in dataset_dict.get('keywords', []):
            items = [
                ('keywords', SCHEMA.keywords, None, Literal),
            ]
            self._add_multilang_triples_from_dict(
                dataset_dict,
                dataset_ref,
                items
            )

    def _distribution_basic_fields_graph(self, distribution, resource_dict):
        items = [
            ('issued', SCHEMA.datePublished, None, Literal),
            ('modified', SCHEMA.dateModified, None, Literal),
        ]

        self._add_triples_from_dict(resource_dict, distribution, items)

        items = [
            ('title', SCHEMA.name, None, Literal),
            ('description', SCHEMA.description, None, Literal),
        ]
        self._add_multilang_triples_from_dict(
            resource_dict,
            distribution,
            items
        )

    def contact_details(self, dataset_dict, dataset_ref, g):
        # Contact details used by graph_from_dataset
        if dataset_dict.get("contact_points"):
            contact_points = self._get_dataset_value(
                dataset_dict, "contact_points"
            )  # noqa
            for contact_point in contact_points:
                contact_details = BNode()
                contact_point_email = \
                    EMAIL_MAILTO_PREFIX + contact_point["email"]
                contact_point_name = contact_point["name"]

                g.add((contact_details, RDF.type, VCARD.Organization))
                g.add(
                    (contact_details, VCARD.hasEmail,
                     URIRef(contact_point_email))
                )  # noqa
                g.add((contact_details, VCARD.fn, Literal(contact_point_name)))

                g.add((dataset_ref, SCHEMA.contactPoint, contact_details))

        return g

    def download_access_url(self, resource_dict, distribution, g):
        # Download URL & Access URL used by graph_from_dataset
        download_url = resource_dict.get("download_url")
        if download_url:
            try:
                download_url = dh.uri_to_iri(download_url)
                g.add((distribution, SCHEMA.downloadURL,
                       URIRef(download_url)))
            except ValueError:
                # only add valid URL
                pass

        url = resource_dict.get("url")
        if (url and not download_url) or (url and url != download_url):
            try:
                url = dh.uri_to_iri(url)
                g.add((distribution, SCHEMA.accessURL, URIRef(url)))
            except ValueError:
                # only add valid URL
                pass
        elif download_url:
            g.add((distribution, SCHEMA.accessURL, URIRef(download_url)))

        return g

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        dataset_uri = dh.dataset_uri(dataset_dict, dataset_ref)
        dataset_ref = URIRef(dataset_uri)
        g = self.g

        # Contact details
        self.contact_details(dataset_dict, dataset_ref, g)

        # Resources
        for resource_dict in dataset_dict.get("resources", []):
            distribution = URIRef(dh.resource_uri(resource_dict))

            g.add((dataset_ref, SCHEMA.distribution, distribution))
            g.add((distribution, RDF.type, SCHEMA.Distribution))

            #  Simple values
            items = [
                ("status", ADMS.status, None, Literal),
                ("coverage", DCT.coverage, None, Literal),
                ("identifier", DCT.identifier, None, Literal),
                ("spatial", DCT.spatial, None, Literal),
            ]

            self._add_triples_from_dict(resource_dict, distribution, items)

            self._add_multilang_value(
                distribution, DCT.title, "display_name", resource_dict
            )  # noqa
            self._add_multilang_value(
                distribution, DCT.description, "description", resource_dict
            )  # noqa

            #  Lists
            items = [
                ("language", DCT.language, None, Literal),
            ]
            self._add_list_triples_from_dict(resource_dict, distribution,
                                             items)

            # Download URL & Access URL
            self.download_access_url(resource_dict, distribution, g)

            # Dates
            items = [
                ("issued", DCT.issued, None, Literal),
                ("modified", DCT.modified, None, Literal),
            ]

            self._add_date_triples_from_dict(resource_dict, distribution,
                                             items)
            # ByteSize
            if resource_dict.get("byte_size"):
                g.add(
                    (distribution, SCHEMA.byteSize,
                     Literal(resource_dict["byte_size"]))
                )

        super(SwissSchemaOrgProfile, self).graph_from_dataset(dataset_dict,
                                                              dataset_ref)

    def parse_dataset(self, dataset_dict, dataset_ref):
        super(SwissSchemaOrgProfile, self).parse_dataset(dataset_dict,
                                                         dataset_ref)

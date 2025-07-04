import json

import ckan.plugins as p
import ckan.model as model
import ckan.plugins.toolkit as tk

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
from ckanext.dcatapchharvest.dcat_helpers import get_pagination
from ckanext.dcatapchharvest.harvest_helper import (
    map_resources_to_ids,
    check_package_change,
    create_activity,
)

import logging
log = logging.getLogger(__name__)


class SwissDCATRDFHarvester(DCATRDFHarvester):
    p.implements(IDCATRDFHarvester, inherit=True)

    harvest_job = None
    current_page_url = None

    def info(self):
        return {
            'name': 'dcat_ch_rdf',
            'title': 'DCAT-AP Switzerland RDF Harvester',
            'description': 'Harvester for DCAT-AP Switzerland datasets from an RDF graph'  # noqa
        }

    def validate_config(self, source_config):
        source_config = super(SwissDCATRDFHarvester, self).validate_config(source_config)  # noqa

        if not source_config:
            return source_config

        source_config_obj = json.loads(source_config)

        if 'excluded_dataset_identifiers' in source_config_obj:
            excluded_dataset_identifiers = source_config_obj['excluded_dataset_identifiers']  # noqa
            if not isinstance(excluded_dataset_identifiers, list):
                raise ValueError('excluded_dataset_identifiers must be '
                                 'a list of strings')
            if not all(isinstance(item, str)
                       for item in excluded_dataset_identifiers):
                raise ValueError('excluded_dataset_identifiers must be '
                                 'a list of strings')

        if 'excluded_license' in source_config_obj:
            excluded_license = source_config_obj['excluded_license']
            if not isinstance(excluded_license, list):
                raise ValueError('excluded_license must be '
                                 'a list of strings')
            if not all(isinstance(item, str)
                       for item in excluded_license):
                raise ValueError('excluded_license must be '
                                 'a list of strings')

        return source_config

    def before_download(self, url, harvest_job):
        # save the harvest_job on the instance
        self.harvest_job = harvest_job
        self.current_page_url = url

        # fix broken URL for City of Zurich
        url = url.replace('ogd.global.szh.loc', 'data.stadt-zuerich.ch')
        return url, []

    def _get_guid(self, dataset_dict, source_url=None):  # noqa
        '''
        Try to get a unique identifier for a harvested dataset
        It will be the first found of:
         * URI (rdf:about)
         * dct:identifier
         * Source URL + Dataset name
         * Dataset name
         The last two are obviously not optimal, as depend on title, which
         might change.
         Returns None if no guid could be decided.
        '''
        guid = None

        if dataset_dict.get('identifier'):
            guid = dataset_dict['identifier']
            # check if the owner_org matches the identifier
            try:
                if '@' in guid:
                    org_name = guid.split('@')[-1]  # get last element
                    org = model.Group.by_name(org_name)
                    if not org:
                        error_msg = (
                            'The organization in the dataset identifier (%s) '
                            'does not not exist. ' % org_name
                        )
                        log.error(error_msg)
                        self._save_gather_error(error_msg, self.harvest_job)
                        return None

                    if org.id != dataset_dict['owner_org']:
                        error_msg = (
                            'The organization in the dataset identifier (%s) '
                            'does not match the organization in the harvester '
                            'config (%s)' % (org.id, dataset_dict['owner_org'])
                        )
                        log.error(error_msg)
                        self._save_gather_error(error_msg, self.harvest_job)
                        return None
            except Exception as e:
                log.exception("Error when getting identifier: %s" % e)
                return None
            return dataset_dict['identifier']

        for extra in dataset_dict.get('extras', []):
            if extra['key'] == 'uri' and extra['value']:
                return extra['value']

        if dataset_dict.get('uri'):
            return dataset_dict['uri']

        for extra in dataset_dict.get('extras', []):
            if extra['key'] == 'identifier' and extra['value']:
                return extra['value']

        for extra in dataset_dict.get('extras', []):
            if extra['key'] == 'dcat_identifier' and extra['value']:
                return extra['value']

        if dataset_dict.get('name'):
            guid = dataset_dict['name']
            if source_url:
                guid = source_url.rstrip('/') + '/' + guid

        return guid

    def _gen_new_name(self, title):
        return super(SwissDCATRDFHarvester, self)._gen_new_name(_derive_flat_title(title))  # noqa

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        try:
            source_config_obj = json.loads(harvest_object.job.source.config)
            for excluded_dataset_identifier in source_config_obj.get('excluded_dataset_identifiers', []):  # noqa
                if excluded_dataset_identifier == dataset_dict.get('identifier'):  # noqa
                    dataset_dict.clear()
            excluded_license = source_config_obj.get('excluded_license', [])
            dataset_license = set([res.get('license') for res in dataset_dict.get('resources', [])])  # noqa
            if [license for license in dataset_license if license in excluded_license]:  # noqa
                dataset_dict.clear()
        except ValueError:
            pass

    def before_update(self, harvest_object, dataset_dict, temp_dict):
        existing_pkg = map_resources_to_ids(dataset_dict, dataset_dict['name'])
        package_changed, msg = check_package_change(existing_pkg, dataset_dict)
        if package_changed:
            create_activity(package_id=dataset_dict['id'], message=msg)

    def after_download(self, content, harvest_job):
        if not content:
            after_download_error_msg = \
                'The content of page-url {} could not be read'.format(
                    self.current_page_url
                )
            log.info(after_download_error_msg)
            return False, [after_download_error_msg]
        return content, []

    def after_parsing(self, rdf_parser, harvest_job):
        parsed_content = rdf_parser.datasets()
        dataset_identifiers = [dataset.get('identifier')
                               for dataset in parsed_content]
        pagination = get_pagination(rdf_parser.g)
        log.debug("pagination-info: {}".format(pagination))
        if not dataset_identifiers:
            after_parsing_error_msg = \
                'The content of page-url {} could not be parsed. ' \
                'Therefore the harvesting was stopped.' \
                'Pagination info: {}'.format(self.page_url, pagination)
            log.info(after_parsing_error_msg)
            return False, [after_parsing_error_msg]
        log.debug("datasets parsed: {}".format(','.join(dataset_identifiers)))
        return rdf_parser, []


def _derive_flat_title(title_dict):
    """localizes language dict if no language is specified"""
    return title_dict.get('de') or title_dict.get('fr') or title_dict.get('en') or title_dict.get('it') or ""  # noqa


class SwissDCATI14YRDFHarvester(SwissDCATRDFHarvester):

    def info(self):
        info = super(SwissDCATI14YRDFHarvester, self).info()

        info['name'] = 'dcat_ch_i14y_rdf'
        info['title'] = 'DCAT-AP Switzerland I14Y RDF Harvester'
        info['description'] = \
            'Harvester for DCAT-AP Switzerland datasets from ' \
            'an RDF graph designed for I14Y'

        return info

    def _get_guid(self, dataset_dict, source_url=None):
        guid = super(SwissDCATI14YRDFHarvester, self).\
            _get_guid(dataset_dict, source_url)

        # get organization name
        try:
            dataset_organization = tk.get_action('organization_show')(
                {},
                {'id': dataset_dict['owner_org']}
            )
            dataset_organization_name = dataset_organization['name']

        except tk.ObjectNotFound:
            raise ValueError(
                'The selected organization was not found.'
            )

        # identifier that has form of <id>,
        # should be changed to the form <id>@<slug>,
        # where slug is an organization name
        if (dataset_dict.get('identifier')
                and dataset_dict['identifier'] == guid
                and '@' not in guid):
            dataset_dict['identifier_i14y'] =\
                dataset_dict['identifier']
            dataset_dict['identifier'] =\
                dataset_dict['identifier'] + '@'\
                + dataset_organization_name

        return dataset_dict['identifier']

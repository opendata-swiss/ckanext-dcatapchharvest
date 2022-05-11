import json
import traceback
from rdflib.exceptions import ParserError

import ckan.plugins as p
import ckan.logic as logic
import ckan.model as model

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
from ckanext.dcatapchharvest.logic import (only_deletion_harvest_objects,
                                           mark_harvest_objects_errored)

import logging
log = logging.getLogger(__name__)


class SwissDCATRDFHarvester(DCATRDFHarvester):
    p.implements(IDCATRDFHarvester, inherit=True)

    harvest_job = None

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
            if not all(isinstance(item, basestring)
                       for item in excluded_dataset_identifiers):
                raise ValueError('excluded_dataset_identifiers must be '
                                 'a list of strings')

        if 'excluded_rights' in source_config_obj:
            excluded_rights = source_config_obj['excluded_rights']
            if not isinstance(excluded_rights, list):
                raise ValueError('excluded_rights must be '
                                 'a list of strings')
            if not all(isinstance(item, basestring)
                       for item in excluded_rights):
                raise ValueError('excluded_rights must be '
                                 'a list of strings')

        return source_config

    def before_download(self, url, harvest_job):
        # save the harvest_job on the instance
        self.harvest_job = harvest_job

        # fix broken URL for City of Zurich
        url = url.replace('ogd.global.szh.loc', 'data.stadt-zuerich.ch')
        return url, []

    def _get_guid(self, dataset_dict, source_url=None):  # noqa
        '''
        Try to get a unique identifier for a harvested dataset
        It will be the first found of:
         * URI (rdf:about)
         * dcat:identifier
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
            except:
                log.exception("An error occured")
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
            excluded_rights = source_config_obj.get('excluded_rights', [])
            dataset_rights = set([res.get('rights') for res in dataset_dict.get('resources', [])])  # noqa
            if [rights for rights in dataset_rights if rights in excluded_rights]:  # noqa
                dataset_dict.clear()
        except ValueError:
            pass

    def before_update(self, harvest_object, dataset_dict, temp_dict):
        # get existing pkg_dict with incoming pkg_name
        site_user = logic.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {})
        context = {
            'model': model,
            'session': model.Session,
            'ignore_auth': True,
            'user': site_user['name'],
        }
        existing_pkg = p.toolkit.get_action('package_show')(context, {
            'id': dataset_dict.get('name')})

        # get existing resource-identifiers
        existing_resources = existing_pkg.get('resources')
        resource_mapping = {r.get('identifier'): r.get('id') for r in existing_resources if r.get('identifier')}  # noqa

        # Try to match existing identifiers with new ones
        # Note: in ckanext-dcat a mapping is already done based on the URI
        #       which will be overwritten here, i.e. the mapping by identifier
        #       has precedence
        for resource in dataset_dict.get('resources'):
            identifier = resource.get('identifier')
            if identifier and identifier in resource_mapping:
                resource['id'] = resource_mapping[identifier]

    def gather_stage(self, harvest_job):
        """Override method to add additional checks in case of bad data
        received from source.
        """
        object_ids = []

        try:
            object_ids = super(SwissDCATRDFHarvester, self)\
                .gather_stage(harvest_job)
        except ParserError as e:
            self._save_gather_error(
                "Error when processsing dataset: %r / %s"
                % (e, traceback.format_exc()),
                harvest_job,
                )

            return []

        if len(object_ids) == 0:
            # This doesn't necessarily mean we got no datasets from the
            # source: if there are multiple pages of results, we might have
            # been able to parse some of them before getting an error back for
            # a later page. In this case, the parent method stops paging
            # through results and returns []. The harvest objects from
            # earlier pages have already been created, however. The next time
            # the run command is run, these harvest objects will be added to
            # the fetch queue.
            #
            # If we end up here, an error *should* have been logged earlier,
            # but let's log one in case it hasn't.
            self._save_gather_error(
                "Error parsing datasets from source url. "
                "This could be because no data was returned, or the data "
                "could not be parsed as RDF.",
                harvest_job,
            )

            return object_ids

        if only_deletion_harvest_objects(object_ids):
            # If we only got harvest objects to delete datasets, save an error
            # and mark all the objects as errored.
            #
            # Again, this does not guarantee that no datasets at all will be
            # deleted, because the harvest objects have been created in the
            # parent method. If the harvest run command is run before they are
            # marked as errored, it will add them to the fetch queue, and some
            # might be processed before we can stop them. At least this logs
            # the error so it is clear what happened.
            self._save_gather_error(
                "Received no datasets from the source: "
                "all existing datasets would be deleted! "
                "Removing the deletions from the queue, but it is possible "
                "that some datasets have already been deleted. Please check.",
                harvest_job,
            )

            mark_harvest_objects_errored(object_ids)

            return []

        return object_ids


def _derive_flat_title(title_dict):
    """localizes language dict if no language is specified"""
    return title_dict.get('de') or title_dict.get('fr') or title_dict.get('en') or title_dict.get('it') or ""  # noqa

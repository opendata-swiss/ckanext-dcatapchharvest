import ckan.plugins.toolkit as tk
import ckan.model as model
from dateutil.parser import parse as dateutil_parse

import logging

log = logging.getLogger(__name__)

NOTIFICATION_USER = 'harvest-notification'


def map_resources_to_ids(pkg_dict, package_id):
    existing_package = \
        tk.get_action('package_show')({}, {'id': package_id})
    existing_resources = existing_package.get('resources')
    existing_resources_mapping = \
        {r['id']: _get_resource_id_string(r) for r in existing_resources}
    for resource in pkg_dict.get('resources'):
        resource_id_dict = _get_resource_id_string(resource)
        id_to_reuse = [k for k, v in existing_resources_mapping.items()
                       if v == resource_id_dict]
        if id_to_reuse:
            id_to_reuse = id_to_reuse[0]
            resource['id'] = id_to_reuse
            del existing_resources_mapping[id_to_reuse]
    return existing_package


def create_activity(package_id):
    notification_user = tk.get_action('user_show')(
        {},
        {'id': NOTIFICATION_USER}
    )
    activity_dict = {
        'user_id': notification_user['id'],
        'object_id': package_id,
        'activity_type': 'changed package',
    }
    activity_create_context = {
        'model': model,
        'user': NOTIFICATION_USER,
        'defer_commit': True,
        'ignore_auth': True,
        'session': model.Session
    }
    tk.get_action('activity_create')(activity_create_context, activity_dict)


def check_package_change(existing_pkg, dataset_dict):
    if _changes_in_date(existing_pkg['modified'], dataset_dict['modified']):
        return True
    resource_count_changed = len(existing_pkg.get('resources')) != \
        len(dataset_dict.get('resources'))
    if resource_count_changed:
        return True
    for resource in dataset_dict.get('resources'):
        matching_existing_resource = [
            existing_resource
            for existing_resource in existing_pkg['resources']
            if existing_resource['id'] == resource['id']
        ]
        if not matching_existing_resource:
            return True
        matching_existing_resource = \
            matching_existing_resource[0]
        if matching_existing_resource.get('url') != resource.get('url'):
            return True
        download_url_changed = \
            matching_existing_resource.get('download_url') != \
            resource.get('download_url')
        if download_url_changed:
            return True
        if _changes_in_date(matching_existing_resource.get('modified'),
                            resource.get('modified')):
            return True
    return False


def _get_resource_id_string(resource):
    return resource.get('url')


def _changes_in_date(ogdch_date, isodate_date):
    if not ogdch_date and not isodate_date:
        return False
    if not ogdch_date or not isodate_date:
        return True
    datetime_from_ogdch_date = dateutil_parse(ogdch_date, dayfirst=True)
    datetime_from_isodate_date = dateutil_parse(isodate_date)
    if datetime_from_ogdch_date.date() == datetime_from_isodate_date.date():
        return False
    return True

from ckan import model
from ckanext.harvest.model import HarvestObjectExtra
import logging

log = logging.getLogger(__name__)


def only_deletion_harvest_objects(object_ids):
    extras = model.Session.query(HarvestObjectExtra)\
        .filter(HarvestObjectExtra.harvest_object_id.in_(object_ids)).all()

    statuses = set([extra.value for extra in extras if extra.key == 'status'])
    if statuses != {u'delete'}:
        return False

    # Todo: Also need to set all the states of the harvest objects to something
    # that isn't WAITING, so they will not be re-queued!
    return True

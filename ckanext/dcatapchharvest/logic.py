from ckan import model
from ckanext.harvest.model import HarvestObject
import logging

log = logging.getLogger(__name__)


def only_deletion_harvest_objects(object_ids):
    extras = model.Session.query(HarvestObject.extras)\
        .filter(HarvestObject.id.in_(object_ids)).all()

    states = set([extra.value for extra in extras if extra.key == 'state'])

    return states == {'delete'}

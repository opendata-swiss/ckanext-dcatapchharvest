from ckan import model
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
import logging

log = logging.getLogger(__name__)


def only_deletion_harvest_objects(object_ids):
    extras = model.Session.query(HarvestObjectExtra)\
        .filter(HarvestObjectExtra.harvest_object_id.in_(object_ids)).all()

    statuses = set([extra.value for extra in extras if extra.key == 'status'])
    if statuses != {u'delete'}:
        return False

    return True


def mark_harvest_objects_errored(object_ids):
    objects = model.Session.query(HarvestObject)\
        .filter(HarvestObject.id.in_(object_ids)).all()

    for obj in objects:
        if obj.state not in ('COMPLETE', 'ERROR'):
            old_state = obj.state
            obj.state = 'ERROR'
            log.info('Harvest object changed state from "%s" to "%s": %s',
                     old_state, obj.state, obj.id)
        else:
            log.info('Harvest object not changed from "%s": %s',
                     obj.state, obj.id)

    model.repo.commit_and_remove()

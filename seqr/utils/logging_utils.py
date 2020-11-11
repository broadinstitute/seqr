import json
import logging

class JsonLogFormatter(logging.Formatter):

    def usesTime(self):
        return True

    def formatMessage(self, record):
        log_json = {'timestamp': record.asctime, 'severity': record.levelname}
        if hasattr(record, 'http_request_json'):
            log_json['httpRequest'] = record.http_request_json
            if getattr(record, 'request_body', None):
                log_json['requestBody'] = record.request_body

        if record.message:
            log_json['message'] = record.message

        if getattr(record, 'user', None) and record.user.is_authenticated():
            log_json['user'] = record.user.email

        if hasattr(record, 'db_update'):
            log_json['dbUpdate'] = record.db_update

        return json.dumps(log_json)


def log_model_update(logger, model, user, update_type, update_fields=None):
    db_entity = type(model).__name__
    entity_id = getattr(model, 'guid', model.pk)
    db_update = {
        'dbEntity': db_entity, 'entityId': entity_id, 'updateType': update_type,
    }
    if update_fields:
        db_update['updateFields'] = list(update_fields)
    logger.info('{} {} {}'.format(update_type, db_entity, entity_id), extra={'user': user, 'db_update': db_update})


def log_model_bulk_update(logger, models, user, update_type, update_fields=None):
    if not models:
        return []
    db_entity = type(models[0]).__name__
    entity_ids = [o.guid for o in models]
    db_update = {
        'dbEntity': db_entity, 'entityIds': entity_ids, 'updateType': 'bulk_{}'.format(update_type),
    }
    if update_fields:
        db_update['updateFields'] = list(update_fields)
    logger.info(
        '{} {} {}s'.format(update_type, len(entity_ids), db_entity), extra={'user': user, 'db_update': db_update})
    return entity_ids
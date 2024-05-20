import json
import logging

from settings import DEPLOYMENT_TYPE
from typing import Optional

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

        if getattr(record, 'user', None) and record.user.is_authenticated:
            log_json['user'] = record.user.email
        elif getattr(record, 'user_email', None):
            log_json['user'] = record.user_email

        if hasattr(record, 'db_update'):
            log_json['dbUpdate'] = record.db_update

        if getattr(record, 'traceback', None):
            log_json['traceback'] = record.traceback

        if getattr(record, 'detail', None):
            log_json['detail'] = record.detail

        if record.levelname == 'ERROR' and DEPLOYMENT_TYPE != 'dev':
            # Allows GCP Error to detect that this is an error log
            log_json['@type'] = 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'

        return json.dumps(log_json)


class SeqrLogger(object):

    def __init__(self, name: Optional[str] = None) -> None:
        """Custom logger which requires user metadata to be included in the log."""
        self._logger = logging.getLogger(name)

    def _log(self, level, message, user, **kwargs):
        self._logger.log(level, message, extra=dict(user=user, **kwargs))

    def debug(self, *args, **kwargs):\
        self._log(logging.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self._log(logging.INFO, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self._log(logging.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs):
        self._log(logging.ERROR, *args, **kwargs)


def log_model_update(logger, model, user, update_type, update_fields=None):
    db_entity = type(model).__name__
    entity_id = getattr(model, 'guid', model.pk)
    db_update = {
        'dbEntity': db_entity, 'entityId': entity_id, 'updateType': update_type,
    }
    if update_fields:
        db_update['updateFields'] = list(update_fields)
    logger.info('{} {} {}'.format(update_type, db_entity, entity_id), user, db_update=db_update)


def log_model_bulk_update(logger, models, user, update_type, update_fields=None):
    if not models:
        return []
    db_entity = type(models[0]).__name__
    entity_ids = sorted([o.guid for o in models])
    db_update = {
        'dbEntity': db_entity, 'entityIds': entity_ids, 'updateType': 'bulk_{}'.format(update_type),
    }
    if update_fields:
        db_update['updateFields'] = list(update_fields)
    logger.info(
        '{} {} {}s'.format(update_type, len(entity_ids), db_entity), user, db_update=db_update)
    return entity_ids

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
        else:
            log_json['message'] = record.message

        if getattr(record, 'user', None) and record.user.is_authenticated():
            log_json['user'] = record.user.email

        if hasattr(record, 'db_update'):
            log_json['dbUpdate'] = record.db_update

        return json.dumps(log_json)
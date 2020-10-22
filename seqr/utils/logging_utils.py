import json
import logging

class JsonLogFormatter(logging.Formatter):

    def usesTime(self):
        return True

    def formatMessage(self, record):
        log_json = {'timestamp': record.asctime, 'severity': record.levelname}
        if hasattr(record, 'http_request_json'):
            log_json['httpRequest'] = record.http_request_json
            log_json.update(record.additional_http_request_json)
        else:
            log_json['message'] = record.message
        return json.dumps(log_json)
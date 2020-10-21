import json
import logging

class JsonLogFormatter(logging.Formatter):

    def usesTime(self):
        return True

    def _parse_http_request(self, record):
        size = ''
        if len(record.args) > 2 and record.args[2].isdigit():
            size = int(record.args[2])
        #import pdb; pdb.set_trace()
        return {
          'requestMethod': '',
          'requestUrl': '',
          'requestSize': size,
          'status': record.status_code,
          'responseSize': '',
          'userAgent': '',
          'remoteIp': '',
          'serverIp': '',
          'referer': '',
          'latency': '',
          'cacheLookup': '',
          'cacheHit': '',
          'cacheValidatedWithOriginServer': '',
          'cacheFillBytes': '',
          'protocol': ''
        }

    def formatMessage(self, record):
        log_json = {'timestamp': record.asctime, 'severity': record.levelname, 'message': record.message}
        if record.request and record.status_code:
            log_json['httpRequest'] = self._parse_http_request(record)
        return json.dumps(log_json)
import requests
from django.core.exceptions import PermissionDenied

from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.terra_api_utils import is_google_authenticated

from settings import AIRTABLE_API_KEY, AIRTABLE_URL

logger = SeqrLogger(__name__)

RDG_BASE = 'RDG'
AIRTABLE_BASES = {
    RDG_BASE: 'app3Y97xtbbaOopVR'
}

class AirtableSession(object):

    def __init__(self, user, base=RDG_BASE):
        if not (is_google_authenticated(user) and user.email.endswith('broadinstitute.org')):
            raise PermissionDenied('Error: To access airtable user must login with Google authentication.')
        self._user = user
        self._url = f'{AIRTABLE_URL}/{AIRTABLE_BASES[base]}'

        self._session = requests.Session()
        self._session.headers.update({'Authorization': f'Bearer {AIRTABLE_API_KEY}'})

    def fetch_records(self, record_type, fields, or_filters):
        filter_formulas = []
        for key, values in or_filters.items():
            filter_formulas += [f"{key}='{value}'" for value in values]
        self._session.params.update({'fields[]': fields, 'filterByFormula': f'OR({",".join(filter_formulas)})'})
        records = {}
        self._populate_records(record_type, records)
        logger.info('Fetched {} {} records from airtable'.format(len(records), record_type), self._user)
        return records

    def _populate_records(self, record_type, records, offset=None):
        response = self._session.get(f'{self._url}/{record_type}', params={'offset': offset} if offset else None)
        response.raise_for_status()
        try:
            response_json = response.json()
            records.update({record['id']: record['fields'] for record in response_json['records']})
        except (ValueError, KeyError) as e:
            raise Exception(f'Unable to retrieve airtable data: {e}')

        if response_json.get('offset'):
            self._populate_records(record_type, records, offset=response_json['offset'])



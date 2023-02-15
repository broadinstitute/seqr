import requests
from django.core.exceptions import PermissionDenied

from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.terra_api_utils import is_google_authenticated

from settings import AIRTABLE_API_KEY, AIRTABLE_URL

logger = SeqrLogger(__name__)

PAGE_SIZE = 100
MAX_OR_FILTERS = PAGE_SIZE - 5


class AirtableSession(object):

    RDG_BASE = 'RDG'
    ANVIL_BASE = 'AnVIL'
    AIRTABLE_BASES = {
        RDG_BASE: 'app3Y97xtbbaOopVR',
        ANVIL_BASE: 'appUelDNM3BnWaR7M',
    }

    def __init__(self, user, base=RDG_BASE):
        self._user = user
        self._check_user_access(base)
        self._url = f'{AIRTABLE_URL}/{self.AIRTABLE_BASES[base]}'

        self._session = requests.Session()
        self._session.headers.update({'Authorization': f'Bearer {AIRTABLE_API_KEY}'})

    def _check_user_access(self, base):
        has_access = is_google_authenticated(self._user)
        if base != self.ANVIL_BASE:
            has_access &= self._user.email.endswith('broadinstitute.org')
        if not has_access:
            raise PermissionDenied('Error: To access airtable user must login with Google authentication.')

    def safe_create_record(self, record_type, record):
        try:
            response = self._session.post(f'{self._url}/{record_type}', json={'records': [{'fields': record}]})
            response.raise_for_status()
        except Exception as e:
            logger.error(f'Airtable create "{record_type}" error: {e}', self._user)

    def fetch_records(self, record_type, fields, or_filters):
        self._session.params.update({'fields[]': fields, 'pageSize': PAGE_SIZE})
        filter_formulas = []
        for key, values in or_filters.items():
            filter_formulas += [f"{key}='{value}'" for value in sorted(values)]
        records = {}
        for i in range(0, len(filter_formulas), MAX_OR_FILTERS):
            filter_formula_group = filter_formulas[i:i + MAX_OR_FILTERS]
            self._session.params.update({'filterByFormula': f'OR({",".join(filter_formula_group)})'})
            logger.info(f'Fetching {record_type} records {i}-{i + len(filter_formula_group)} from airtable', self._user)
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



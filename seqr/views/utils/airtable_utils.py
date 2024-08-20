import requests
from collections import defaultdict
from django.core.exceptions import PermissionDenied
import re

from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.terra_api_utils import is_google_authenticated

from settings import AIRTABLE_API_KEY, AIRTABLE_URL, BASE_URL

logger = SeqrLogger(__name__)

PAGE_SIZE = 100
MAX_OR_FILTERS = PAGE_SIZE - 5

ANVIL_REQUEST_TRACKING_TABLE = 'AnVIL Seqr Loading Requests Tracking'

LOADABLE_PDO_STATUSES = [
    'On hold for phenotips, but ready to load',
    'Methods (Loading)',
]


class AirtableSession(object):

    RDG_BASE = 'RDG'
    ANVIL_BASE = 'AnVIL'
    AIRTABLE_BASES = {
        RDG_BASE: 'app3Y97xtbbaOopVR',
        ANVIL_BASE: 'appUelDNM3BnWaR7M',
    }

    def __init__(self, user, base=RDG_BASE, no_auth=False):
        self._user = user
        if not no_auth:
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

    def safe_patch_records(self, record_type, record_or_filters, record_and_filters, update, max_records=PAGE_SIZE - 1):
        try:
            self._patch_record(record_type, record_or_filters, record_and_filters, update, max_records)
        except Exception as e:
            logger.error(f'Airtable patch "{record_type}" error: {e}', self._user, detail={
                'or_filters': record_or_filters, 'and_filters': record_and_filters, 'update': update,
            })

    def _patch_record(self, record_type, record_or_filters, record_and_filters, update, max_records):
        records = self.fetch_records(
            record_type, fields=record_or_filters.keys(), or_filters=record_or_filters, and_filters=record_and_filters,
            page_size=max_records+1,
        )
        if not records or len(records) > max_records:
            raise ValueError('Unable to identify record to update')

        self._session.params = {}
        errors = []
        for record_id in records.keys():
            try:
                response = self._session.patch(f'{self._url}/{record_type}/{record_id}', json={'fields': update})
                response.raise_for_status()
            except Exception as e:
                errors.append(str(e))

        if errors:
            raise Exception(';'.join(errors))

    def fetch_records(self, record_type, fields, or_filters, and_filters=None, page_size=PAGE_SIZE):
        self._session.params.update({'fields[]': fields, 'pageSize': page_size})
        filter_formulas = []
        for key, values in or_filters.items():
            filter_formulas += [f"{key}='{value}'" for value in sorted(values)]
        and_filter_formulas = ','.join([f"{{{key}}}='{value}'" for key, value in (and_filters or {}).items()])
        records = {}
        for i in range(0, len(filter_formulas), MAX_OR_FILTERS):
            filter_formula_group = filter_formulas[i:i + MAX_OR_FILTERS]
            filter_formula = f'OR({",".join(filter_formula_group)})'
            if and_filters:
                filter_formula = f'AND({and_filter_formulas},{filter_formula})'
            self._session.params.update({'filterByFormula': filter_formula})
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

    def _get_samples_for_id_field(self, sample_ids, id_field, fields):
        raw_records = self.fetch_records(
            'Samples', fields=[id_field] + fields,
            or_filters={f'{{{id_field}}}': sample_ids},
        )

        records_by_id = defaultdict(list)
        for airtable_id, record in raw_records.items():
            records_by_id[record[id_field]].append({**record, 'airtable_id': airtable_id})
        return records_by_id

    def get_samples_for_sample_ids(self, sample_ids, fields):
        records_by_id = self._get_samples_for_id_field(sample_ids, 'CollaboratorSampleID', fields)
        missing = set(sample_ids) - set(records_by_id.keys())
        if missing:
            records_by_id.update(self._get_samples_for_id_field(missing, 'SeqrCollaboratorSampleID', fields))
        return records_by_id

    def get_loadable_pdos(self):
        pdos = self.fetch_records(
            'PDO', fields=['PassingCollaboratorSampleIDs', 'SeqrIDs', 'SeqrProjectURL'],
            or_filters={'PDOStatus': LOADABLE_PDO_STATUSES}
        )
        return {record_id: {
            'project_guid': re.match(f'{BASE_URL}project/([^/]+)/project_page', pdo['SeqrProjectURL']).group(1),
            'sample_ids': [sample for sample in pdo['PassingCollaboratorSampleIDs'] + pdo['SeqrIDs'] if sample],
        } for record_id, pdo in pdos.items()}

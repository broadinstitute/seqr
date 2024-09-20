import requests
from collections import defaultdict
from django.core.exceptions import PermissionDenied

from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.terra_api_utils import is_cloud_authenticated

from settings import AIRTABLE_API_KEY, AIRTABLE_URL

logger = SeqrLogger(__name__)

PAGE_SIZE = 100
MAX_OR_FILTERS = PAGE_SIZE - 5
MAX_UPDATE_RECORDS = 10

ANVIL_REQUEST_TRACKING_TABLE = 'AnVIL Seqr Loading Requests Tracking'

LOADABLE_PDO_STATUSES = [
    'On hold for phenotips, but ready to load',
    'Methods (Loading)',
]
AVAILABLE_PDO_STATUS = 'Available in seqr'


class AirtableSession(object):

    RDG_BASE = 'RDG'
    ANVIL_BASE = 'AnVIL'
    AIRTABLE_BASES = {
        RDG_BASE: 'app3Y97xtbbaOopVR',
        ANVIL_BASE: 'appUelDNM3BnWaR7M',
    }

    @staticmethod
    def is_airtable_enabled():
        return bool(AIRTABLE_API_KEY)

    def __init__(self, user, base=RDG_BASE, no_auth=False):
        if not self.is_airtable_enabled():
            raise ValueError('Airtable is not configured')

        self._user = user
        if not no_auth:
            self._check_user_access(base)
        self._url = f'{AIRTABLE_URL}/{self.AIRTABLE_BASES[base]}'

        self._session = requests.Session()
        self._session.headers.update({'Authorization': f'Bearer {AIRTABLE_API_KEY}'})

    def _check_user_access(self, base):
        has_access = is_cloud_authenticated(self._user)
        if base != self.ANVIL_BASE:
            has_access &= self._user.email.endswith('broadinstitute.org')
        if not has_access:
            raise PermissionDenied('Error: To access airtable user must login with Google authentication.')

    def safe_create_records(self, record_type, records):
        return self._safe_bulk_update_records(
            'post', record_type, [{'fields': record} for record in records], error_detail=records,
        )

    def safe_patch_records(self, record_type, record_or_filters, record_and_filters, update, max_records=PAGE_SIZE - 1):
        error_detail = {
            'or_filters': record_or_filters, 'and_filters': record_and_filters, 'update': update,
        }
        try:
            records = self.fetch_records(
                record_type, fields=record_or_filters.keys(), or_filters=record_or_filters,
                and_filters=record_and_filters,
                page_size=max_records + 1,
            )
            if not records or len(records) > max_records:
                raise ValueError('Unable to identify record to update')

            self.safe_patch_records_by_id(record_type, list(records.keys()), update, error_detail=error_detail)
        except Exception as e:
            logger.error(f'Airtable patch "{record_type}" error: {e}', self._user, detail=error_detail)

    def safe_patch_records_by_id(self, record_type, record_ids, update, error_detail=None):
        self._safe_bulk_update_records(
            'patch', record_type, [{'id': record_id, 'fields': update} for record_id in sorted(record_ids)],
            error_detail=error_detail or {'record_ids': record_ids, 'update': update},
        )

    def _safe_bulk_update_records(self, update_type, record_type, records, error_detail=None):
        self._session.params = {}
        update = getattr(self._session, update_type)
        errors = []
        updated_records = []
        for i in range(0, len(records), MAX_UPDATE_RECORDS):
            try:
                response = update(f'{self._url}/{record_type}', json={'records': records[i:i + MAX_UPDATE_RECORDS]})
                response.raise_for_status()
                updated_records += response.json()['records']
            except Exception as e:
                errors.append(str(e))

        if errors:
            logger.error(
                f'Airtable {update_type} "{record_type}" error: {";".join(errors)}', self._user, detail=error_detail,
            )

        return updated_records

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

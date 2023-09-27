import requests
from collections import defaultdict
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


def _get_airtable_samples_for_id_field(sample_ids, id_field, fields, session):
    raw_records = session.fetch_records(
        'Samples', fields=[id_field] + fields,
        or_filters={f'{{{id_field}}}': sample_ids},
    )

    records_by_id = defaultdict(list)
    for record in raw_records.values():
        records_by_id[record[id_field]].append(record)
    return records_by_id


def get_airtable_samples(sample_ids, user, fields, list_fields=None):
    list_fields = list_fields or []
    all_fields = fields + list_fields

    session = AirtableSession(user)
    records_by_id = _get_airtable_samples_for_id_field(sample_ids, 'CollaboratorSampleID', all_fields, session)
    missing = set(sample_ids) - set(records_by_id.keys())
    if missing:
        records_by_id.update(_get_airtable_samples_for_id_field(missing, 'SeqrCollaboratorSampleID', all_fields, session))

    sample_records = {}
    for record_id, records in records_by_id.items():
        parsed_record = {}
        for field in fields:
            record_field = {
                record[field][0] if field == 'Collaborator' else record[field] for record in records if field in record
            }
            if len(record_field) > 1:
                error = 'Found multiple airtable records for sample {} with mismatched values in field {}'.format(
                    record_id, field)
                raise Exception(error)
            if record_field:
                parsed_record[field] = record_field.pop()
        for field in list_fields:
            parsed_record[field] = set()
            for record in records:
                if field in record:
                    parsed_record[field].update(record[field])

        sample_records[record_id] = parsed_record

    return sample_records, session

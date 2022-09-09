import re

from collections import defaultdict

from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.file_utils import file_iter

BLOCK_SIZE = 65536

EXPECTED_META_FIELDS ={
    'INFO': {
        'AC': {
            'Number': 'A',
            'Type': 'Integer',
        },
        'AN': {
            'Number': '1',
            'Type': 'Integer',
        },
        'AF': {
            'Number': 'A',
            'Type': 'Float',
        }
    },
    'FORMAT': {
        'GQ': {
            'Number': '1',
            'Type': 'Integer',
        },
        'GT': {
            'Number': '1',
            'Type': 'String',
        }
    }
}

REQUIRED_HEADERS = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT']


def _validate_vcf(header, meta, first_line):

    missing_headers = [h for h in REQUIRED_HEADERS if h not in header ]
    if missing_headers:
        missing_fields = ','.join(missing_headers)
        raise ErrorsWarningsException([f'Required VCF header fields {missing_fields} are missing.'], [])

    for field, sub_field_meta in EXPECTED_META_FIELDS.items():
        for sub_field, metadata in sub_field_meta.items():
            for key, value in metadata.items():
                if meta.get(field, {}).get(sub_field, {}).get(key) != value:
                    error = f'VCF header field {field}.{sub_field} and meta information {key}={value} is expected.'
                    raise ErrorsWarningsException([error], [])

    row_data = first_line.split('\t')
    info_keys = [k.split('=')[0] for k in row_data[7].split(';')]
    missing_info_fields = [f for f in EXPECTED_META_FIELDS['INFO'].keys() if f not in info_keys ]
    if missing_info_fields:
        missing_fields = ','.join(missing_info_fields)
        raise ErrorsWarningsException([f'Missing INFO field(s) {missing_fields} in the row data'], [])

    format_keys = [k for k in row_data[8].split(':')]
    missing_format_fields = [f for f in EXPECTED_META_FIELDS['FORMAT'].keys() if f not in format_keys]
    if missing_format_fields:
        missing_fields = ','.join(missing_format_fields)
        raise ErrorsWarningsException([f'Missing FORMAT field(s) {missing_fields} in the row data'], [])


def _get_vcf_meta_data(line):
    r = re.search(r'##(.*?)=<(.*)>$', line)
    if r:
        field, value = r.groups()
        value = re.sub(r'".*"', '""', value)  # remove description string which could have '=' or ',' in it
        sub_field_meta = {}
        for k, v in map(lambda s: s.split('='), value.split(',')):
            sub_field_meta[k] = v
        sub_field = sub_field_meta.pop('ID')
        return field, {sub_field: sub_field_meta}
    return None, None


def validate_vcf_and_get_samples(vcf_filename):
    byte_range = None if vcf_filename.endswith('.vcf') else (0, BLOCK_SIZE)
    samples = {}
    meta = defaultdict(dict)
    for line in file_iter(vcf_filename, byte_range=byte_range):
        if line[0] != '#':
            _validate_vcf(header[0:9], meta, line)
            break
        field, sub_field_meta = _get_vcf_meta_data(line)
        if field:
            meta[field].update(sub_field_meta)
        if line.startswith('#CHROM'):
            header = line.rstrip().split('\t')
            samples = set(header[9:])

    return samples

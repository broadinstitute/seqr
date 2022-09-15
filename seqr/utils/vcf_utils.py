import re

from collections import defaultdict

from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.file_utils import file_iter

BLOCK_SIZE = 65536

EXPECTED_META_FIELDS ={
    'INFO': {
        'AC': 'Integer',
        'AN': 'Integer',
        'AF': 'Float'
    },
    'FORMAT': {
        'AD': 'Integer',
        'DP': 'Integer',
        'GQ': 'Integer',
        'GT': 'String'
    }
}

REQUIRED_HEADERS = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT']


def _validate_vcf_header(header):
    missing_headers = [h for h in REQUIRED_HEADERS if h not in header]
    if missing_headers:
        missing_fields = ', '.join(missing_headers)
        raise ErrorsWarningsException([f'Missing required VCF header field(s) {missing_fields}.'], [])


def _validate_vcf_meta(meta):
    errors = []
    for field, sub_field_meta in EXPECTED_META_FIELDS.items():
        missing_meta = [m for m in EXPECTED_META_FIELDS[field] if not meta.get(field, {}).get(m)]
        if missing_meta:
            missing_fields = ', '.join(missing_meta)
            errors.append(f'Missing required {field} field(s) {missing_fields}')
        for sub_field, expected in sub_field_meta.items():
            value = meta.get(field, {}).get(sub_field)
            if value and value != expected:
                errors.append(f'Incorrect meta Type for {field}.{sub_field} - expected "{expected}", got "{value}"')
    if errors:
        raise ErrorsWarningsException(errors, [])


def _get_vcf_meta_data(line):
    r = re.search(r'##(?P<field>.*?)=<ID=(?P<id>[^,]*).*Type=(?P<type>[^,]*).*>$', line)
    if r:
        matches = r.groupdict()
        return matches['field'], {matches['id']: matches['type']}
    return None, None


def validate_vcf_and_get_samples(vcf_filename):
    byte_range = None if vcf_filename.endswith('.vcf') else (0, BLOCK_SIZE)
    samples = set()
    header = []
    meta = defaultdict(dict)
    for line in file_iter(vcf_filename, byte_range=byte_range):
        if line.startswith('#'):
            if line.startswith('#CHROM'):
                header = line.rstrip().split('\t')
                samples = set(header[len(REQUIRED_HEADERS):])
            else:
                field, sub_field_type = _get_vcf_meta_data(line)
                if field:
                    meta[field].update(sub_field_type)
        else:
            break

    _validate_vcf_header(header[0:len(REQUIRED_HEADERS)])
    _validate_vcf_meta(meta)

    return samples

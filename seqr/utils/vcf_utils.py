import re

from collections import defaultdict

from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.file_utils import file_iter, does_file_exist, get_gs_file_list
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS

BLOCK_SIZE = 65536

EXPECTED_META_FIELDS ={
    'FORMAT': {
        'AD': 'Integer',
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


def _get_vcf_meta_info(line):
    r = re.search(r'##(?P<field>.*?)=<ID=(?P<id>[^,]*).*Type=(?P<type>[^,]*).*>$', line)
    if r:
        return r.groupdict()
    return None


def validate_vcf_and_get_samples(vcf_filename):
    byte_range = None if vcf_filename.endswith('.vcf') else (0, BLOCK_SIZE)
    samples = {}
    header = []
    meta = defaultdict(dict)
    for line in file_iter(vcf_filename, byte_range=byte_range):
        if line.startswith('#'):
            if line.startswith('#CHROM'):
                header_cols = line.rstrip().split('\t')
                format_indices = [index for index, col in enumerate(header_cols) if col == 'FORMAT']
                format_index = format_indices[0] + 1 if format_indices else len(header_cols)
                header = header_cols[0:format_index]
                samples = set(header_cols[format_index:])
                break
            else:
                meta_info = _get_vcf_meta_info(line)
                if meta_info:
                    meta[meta_info['field']].update({meta_info['id']: meta_info['type']})
        else:
            raise ErrorsWarningsException(['No header found in the VCF file.'], [])

    _validate_vcf_header(header)
    if not samples:
        raise ErrorsWarningsException(['No samples found in the provided VCF.'], [])
    _validate_vcf_meta(meta)

    return samples


def validate_vcf_exists(data_path, user, path_name=None, allowed_exts=None):
    file_extensions = (allowed_exts or ()) + VCF_FILE_EXTENSIONS
    if not data_path.endswith(file_extensions):
        raise ErrorsWarningsException([
            'Invalid VCF file format - file path must end with {}'.format(' or '.join(file_extensions))
        ])

    file_to_check = None
    if '*' in data_path:
        files = get_gs_file_list(data_path, user, check_subfolders=False, allow_missing=True)
        if files:
            file_to_check = files[0]
    elif does_file_exist(data_path, user=user):
        file_to_check = data_path

    if not file_to_check:
        raise ErrorsWarningsException(['Data file or path {} is not found.'.format(path_name or data_path)])

    return file_to_check

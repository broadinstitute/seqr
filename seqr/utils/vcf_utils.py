import os
import re

from collections import defaultdict

from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.file_utils import file_iter, does_file_exist, list_files
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS
from seqr.models import Sample

BLOCK_SIZE = 65536

BASE_EXPECTED_FORMAT_FIELDS ={
    'GQ': 'Integer',
    'GT': 'String'
}

ALL_EXPECTED_FORMAT_FIELDS ={
    'AD': 'Integer',
    **BASE_EXPECTED_FORMAT_FIELDS,
}

DATA_TYPE_FORMAT_FIELDS = {
    Sample.DATASET_TYPE_SV_CALLS: BASE_EXPECTED_FORMAT_FIELDS,
}

DATA_TYPE_FILE_EXTS = {
    Sample.DATASET_TYPE_MITO_CALLS: ('.mt',),
    Sample.DATASET_TYPE_SV_CALLS: ('.bed', '.bed.gz'),
}

REQUIRED_HEADERS = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT']


def _validate_vcf_header(header):
    missing_headers = [h for h in REQUIRED_HEADERS if h not in header]
    if missing_headers:
        missing_fields = ', '.join(missing_headers)
        raise ErrorsWarningsException([f'Missing required VCF header field(s) {missing_fields}.'], [])


def _validate_vcf_meta(meta, genome_version, dataset_type):
    errors = []
    expected_format_fields = DATA_TYPE_FORMAT_FIELDS.get(dataset_type, ALL_EXPECTED_FORMAT_FIELDS)
    format_meta = meta.get('FORMAT', {})
    missing_meta = [m for m in expected_format_fields if not format_meta.get(m)]
    if missing_meta:
        missing_fields = ', '.join(missing_meta)
        errors.append(f'Missing required FORMAT field(s) {missing_fields}')
    for sub_field, expected in expected_format_fields.items():
        value = format_meta.get(sub_field)
        if value and value != expected:
            errors.append(f'Incorrect meta Type for FORMAT.{sub_field} - expected "{expected}", got "{value}"')

    if 'reference' in meta and len(meta['reference']) == 1:
        meta_version = next(iter(meta['reference'].keys()))
        if meta_version != genome_version:
            errors.append(
                f'Mismatched genome version - VCF metadata indicates GRCh{meta_version}, GRCH{genome_version} provided')

    if errors:
        raise ErrorsWarningsException(errors, [])


def _get_vcf_meta_info(line):
    for meta_regex in [
        r'##(?P<field>.*?)=<ID=(?P<id>[^,]*).*Type=(?P<type>[^,]*).*>$',
        r'##(?P<field>reference)=.*(?P<type>GRCh|grch)(?P<id>3(7|8)).*$',
    ]:
        r = re.search(meta_regex, line)
        if r:
            return r.groupdict()
    return None


def validate_vcf_and_get_samples(data_path, user, genome_version, path_name=None, dataset_type=None):
    allowed_exts = DATA_TYPE_FILE_EXTS.get(dataset_type)

    vcf_filename = _validate_vcf_exists(data_path, user, path_name, allowed_exts)

    if allowed_exts and vcf_filename.endswith(allowed_exts):
        return None

    byte_range = None if vcf_filename.endswith('.vcf') else (0, BLOCK_SIZE)
    meta = defaultdict(dict)
    try:
        header_line = next(_get_vcf_header_line(file_iter(vcf_filename, byte_range=byte_range), meta))
    except StopIteration:
        raise ErrorsWarningsException(['No header found in the VCF file.'], [])
    except UnicodeDecodeError:
        raise ErrorsWarningsException([
            'Unable to read the VCF file. This often occurs when a file is improperly gzipped, or when the file extension does not align with the file type (i.e. a .gz file that is not actually gzipped)'
        ], [])
    header_cols = header_line.rstrip().split('\t')
    format_indices = [index for index, col in enumerate(header_cols) if col == 'FORMAT']
    format_index = format_indices[0] + 1 if format_indices else len(header_cols)
    header = header_cols[0:format_index]
    samples = set(header_cols[format_index:])

    _validate_vcf_header(header)
    if not samples:
        raise ErrorsWarningsException(['No samples found in the provided VCF.'], [])
    _validate_vcf_meta(meta, genome_version, dataset_type)

    return samples


def _get_vcf_header_line(vcf_file, meta):
    for line in vcf_file:
        line_str = line.decode() if isinstance(line, bytes) else line
        if line_str.startswith('#'):
            if line_str.startswith('#CHROM'):
                yield line_str
            else:
                meta_info = _get_vcf_meta_info(line_str)
                if meta_info:
                    meta[meta_info['field']].update({meta_info['id']: meta_info['type']})


def _validate_vcf_exists(data_path, user, path_name, allowed_exts):
    file_extensions = (allowed_exts or ()) + VCF_FILE_EXTENSIONS
    if not data_path.endswith(file_extensions):
        raise ErrorsWarningsException([
            'Invalid VCF file format - file path must end with {}'.format(' or '.join(file_extensions))
        ])

    file_to_check = None
    if '*' in data_path:
        files = list_files(data_path, user)
        if files:
            file_to_check = files[0]
    elif does_file_exist(data_path, user=user):
        file_to_check = data_path

    if not file_to_check:
        raise ErrorsWarningsException(['Data file or path {} is not found.'.format(path_name or data_path)])

    return file_to_check


def get_vcf_list(data_path, user):
    file_list = list_files(data_path, user, check_subfolders=True, allow_missing=False)
    data_path_list = [path.replace(data_path, '') for path in file_list if path.endswith(VCF_FILE_EXTENSIONS)]
    return _merge_sharded_vcf(data_path_list)


def _merge_sharded_vcf(vcf_files):
    files_by_path = defaultdict(list)

    for vcf_file in vcf_files:
        subfolder_path, file = vcf_file.rsplit('/', 1)
        files_by_path[subfolder_path].append(file)

    # discover the sharded VCF files in each folder, replace the sharded VCF files with a single path with '*'
    for subfolder_path, files in files_by_path.items():
        if len(files) < 2:
            continue
        prefix = os.path.commonprefix(files)
        suffix_match = re.fullmatch(r'{}\d*(?P<suffix>\D.*)'.format(prefix), files[0])
        if not suffix_match:
            continue
        suffix = suffix_match.groupdict()['suffix']
        if all([re.fullmatch(r'{}\d+{}'.format(prefix, suffix), file) for file in files]):
            files_by_path[subfolder_path] = [f'{prefix}*{suffix}']

    return [f'{path}/{file}' for path, files in files_by_path.items() for file in files]

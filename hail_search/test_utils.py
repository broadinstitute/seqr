from copy import deepcopy


FAMILY_3_SAMPLE = {
    'sample_id': 'NA20870', 'individual_guid': 'I000007_na20870', 'family_guid': 'F000003_3',
    'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'M',
}
EXPECTED_SAMPLE_DATA = {
    'VARIANTS': [
        {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
        {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
        {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'},
        FAMILY_3_SAMPLE,
    ], 'SV_WES': [
        {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
        {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
        {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'}
    ],
}
CUSTOM_AFFECTED_SAMPLE_DATA = {'VARIANTS': deepcopy(EXPECTED_SAMPLE_DATA['VARIANTS'])}
CUSTOM_AFFECTED_SAMPLE_DATA['VARIANTS'][0]['affected'] = 'N'
CUSTOM_AFFECTED_SAMPLE_DATA['VARIANTS'][1]['affected'] = 'A'
CUSTOM_AFFECTED_SAMPLE_DATA['VARIANTS'][2]['affected'] = 'U'

FAMILY_1_SAMPLE_DATA = {
    'VARIANTS': [
        {'sample_id': 'NA19675', 'individual_guid': 'I000001_na19675', 'family_guid': 'F000001_1', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'M'},
        {'sample_id': 'NA19678', 'individual_guid': 'I000002_na19678', 'family_guid': 'F000001_1', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
    ],
}

ALL_AFFECTED_SAMPLE_DATA = deepcopy(EXPECTED_SAMPLE_DATA)
ALL_AFFECTED_SAMPLE_DATA['MITO'] = [
    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'},
]
FAMILY_5_SAMPLE = {
    'sample_id': 'NA20874', 'individual_guid': 'I000009_na20874', 'family_guid': 'F000005_5', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M',
}
ALL_AFFECTED_SAMPLE_DATA['VARIANTS'].append(FAMILY_5_SAMPLE)


def get_hail_search_body(genome_version='GRCh38', num_results=100, sample_data=None, omit_sample_type=None, **search_body):
    sample_data = sample_data or EXPECTED_SAMPLE_DATA
    if omit_sample_type:
        sample_data = {k: v for k, v in sample_data.items() if k != omit_sample_type}

    search = {
        'sample_data': sample_data,
        'genome_version': genome_version,
        'num_results': num_results,
        **search_body,
    }
    search.update(search_body or {})
    return search

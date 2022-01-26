#!/usr/bin/env python3.7

import csv
import json

def _format_inheritance(inheritance):
    inheritance_mode = (inheritance or {}).get('mode')
    inheritance_filter = (inheritance or {}).get('filter') or {}
    if inheritance_filter.get('genotype'):
        inheritance_mode = None

    return {
        'inheritanceMode': inheritance_mode or ('custom' if inheritance_filter else None),
        'inheritanceFilter': inheritance_filter if (inheritance_filter and not inheritance_mode) else None,
    }

def _dataset_type(annotations, new_svs=False):
    dataset_type = []
    if any(v for k, v in annotations.items() if k != 'structural' and k != 'structural_consequence'):
        dataset_type.append('VARIANTS')
    if new_svs or bool(annotations.get('structural')) or bool(annotations.get('structural_consequence')):
        dataset_type.append('SV')
    return ','.join(dataset_type)

def _parse_annotations(annotations):
    annotations = annotations or {}

    splice_ai = annotations.pop('splice_ai', None)
    new_svs = bool(annotations.pop('new_structural_variants', False))

    return {
        'transcriptConsequences': ', '.join(sorted({ann for anns in annotations.values() for ann in anns})),
        'datasetType': _dataset_type(annotations, new_svs),
        'splice_ai': splice_ai,
    }

def _parse_freqs(frequencies):
    freqs = {f'{k}_af': v['af'] for k, v in frequencies.items() if v.get('af') is not None and v['af'] != 1}
    freqs.update({k: {k2: v2 for k2, v2 in v.items() if k2 != 'af'} for k, v in frequencies.items() if v.get('af') is None})
    return freqs

FORMAT_SEARCH_FIELD = {
    'inheritance': _format_inheritance,
    'pathogenicity': lambda search: {k: ', '.join(v) for k, v in (search or {}).items() if v},
    'annotations': _parse_annotations,
    'annotations_secondary': lambda annotations: {
        'secondaryTranscriptConsequences': ', '.join(sorted({ann for anns in (annotations or {}).values() for ann in anns})),
        'secondaryDatasetType': _dataset_type(annotations or {}),
    },
    'freqs': _parse_freqs,
    'in_silico': lambda search: {k: v for k, v in (search or {}).items() if v is not None and len(v) != 0},
    'locus': lambda search: {
        'genes': search.get('rawItems', '').replace(',', ' ').replace('\n', ' '),
        'variantIds': search.get('rawVariantItems', '').replace(',', ' ').replace('\n', ' '),
        'excludeLocations': search.get('excludeLocations'),
    },
    'qualityFilter': lambda search: {
        'qcFilter': search.get('vcf_filter'),
        **{k: v for k, v in search.items() if k != 'vcf_filter' and v},
    },
}

FREQUENCIES = ['gnomad_genomes', 'gnomad_exomes', 'g1k', 'exac', 'topmed', 'gnomad_svs', 'callset', 'sv_callset']
COLUMNS = [
    'timestamp', 'requestUrl', 'user', 'numProjects', 'numFamilies', 'customSearch',
    'inheritanceMode', 'inheritanceFilter', 'clinvar', 'hgmd', 'datasetType', 'transcriptConsequences',
    'secondaryDatasetType', 'secondaryTranscriptConsequences', 'genes', 'variantIds', 'excludeLocations',
    'min_gq', 'min_ab', 'min_qs', 'min_gq_sv', 'qcFilter', 'splice_ai', 'cadd', 'fathmm', 'mut_taster', 'sift',
    'metasvm', 'revel', 'primate_ai', 'polyphen',
] + [f'{k}_af' for k in FREQUENCIES] + FREQUENCIES


with open('/Users/hsnow/Downloads/downloaded-search-logs-20220125.json', 'rt') as f:
    rows = json.load(f)

formatted_rows = []
for row in rows:
    url = row['httpRequest']['requestUrl']
    if 'download' in url or 'requestBody' not in row['jsonPayload']:
        continue

    formatted_row = {
        'timestamp': row['timestamp'],
        'requestUrl': url,
        'customSearch': 'custom_search' in row['httpRequest']['referer'],
        'user': row['jsonPayload']['user'],
    }

    num_families = None
    if row['jsonPayload']['requestBody'].get('allProjectFamilies'):
        num_projects = 400
    elif row['jsonPayload']['requestBody'].get('projectGuids'):
        num_projects = len(row['jsonPayload']['requestBody']['projectGuids'])
    else:
        num_projects = len(row['jsonPayload']['requestBody']['projectFamilies'])
        num_families =  sum([len(project['familyGuids']) for project in row['jsonPayload']['requestBody']['projectFamilies']])
    formatted_row.update({'numProjects': num_projects, 'numFamilies': num_families})

    for k, v in row['jsonPayload']['requestBody'].get('search', {}).items():
        if k == 'datasetType':
            continue
        formatted_row.update(FORMAT_SEARCH_FIELD[k](v))

    # if formatted_row.get('splice_ai'):
    #     import pdb; pdb.set_trace()
    formatted_rows.append(formatted_row)

with open('parsed_logs.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(formatted_rows)

#!/usr/bin/env python3.7

import csv
import json

with open('/Users/hsnow/Downloads/downloaded-search-logs-subset.json', 'rt') as f:
    rows = json.load(f)

COLUMNS = ['timestamp', 'requestUrl', 'user', 'numProjects', 'numFamilies', 'datasetType', 'inheritance', 'pathogenicity', 'annotations', 'annotations_secondary', 'freqs', 'in_silico', 'locus', 'qualityFilter']

formatted_rows = []
for row in rows:
    formatted_row = {
        'timestamp': row['timestamp'],
        'requestUrl': row['httpRequest']['requestUrl'],
        'user': row['jsonPayload']['user'],
        'numProjects': len(row['jsonPayload']['requestBody']['projectFamilies']),
        'numFamilies': sum([len(project['familyGuids']) for project in row['jsonPayload']['requestBody']['projectFamilies']]),
    }
    formatted_row.update(row['jsonPayload']['requestBody']['search'])
    formatted_rows.append(formatted_row)

with open('parsed_logs.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(formatted_rows)

import React from 'react'

import LoadReportTable from 'shared/components/table/LoadReportTable'
import { BASE_FAMILY_METADATA_COLUMNS } from 'shared/utils/constants'

const VIEW_ALL_PAGES = [{ name: 'Broad', downloadName: 'All', path: 'all' }]

const COLUMNS = [
  ...BASE_FAMILY_METADATA_COLUMNS.map(({ secondaryExportColumn, ...col }) => col),
  { name: 'genes' },
  { name: 'actual_inheritance' },
  { name: 'individual_count', content: '# individuals' },
  { name: 'family_structure' },
  { name: 'proband_id' },
  { name: 'paternal_id' },
  { name: 'maternal_id' },
  { name: 'other_individual_ids' },
  { name: 'analysed_by', style: { minWidth: '400px' } },
]

const FamilyMetadata = props => (
  <LoadReportTable
    columns={COLUMNS}
    viewAllPages={VIEW_ALL_PAGES}
    urlBase="report/family_metadata"
    idField="family_id"
    fileName="Family_Metadata"
    {...props}
  />
)

export default FamilyMetadata

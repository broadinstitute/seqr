import React from 'react'

import LoadReportTable from 'shared/components/table/LoadReportTable'
import { FAMILY_ANALYSIS_STATUS_LOOKUP } from 'shared/utils/constants'

const VIEW_ALL_PAGES = [{ name: 'Broad', downloadName: 'All', path: 'all' }]

const COLUMNS = [
  { name: 'data_type' },
  { name: 'date_data_generation', format: ({ date_data_generation: date }) => date && new Date(date).toLocaleDateString() },
  { name: 'phenotype_description' },
  { name: 'consanguinity' },
  {
    name: 'analysisStatus',
    content: 'analysis_status',
    format: ({ analysisStatus }) => FAMILY_ANALYSIS_STATUS_LOOKUP[analysisStatus]?.name,
  },
  { name: 'solve_status' },
  { name: 'genes' },
  { name: 'actual_inheritance' },
  { name: 'condition_id' },
  { name: 'known_condition_name' },
  { name: 'individual_count', content: '# individuals' },
  { name: 'family_structure' },
  { name: 'proband_id' },
  { name: 'paternal_id' },
  { name: 'maternal_id' },
  { name: 'other_individual_ids' },
  { name: 'analysis_groups' },
  { name: 'pmid_id' },
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

import React from 'react'

import LoadReportTable from 'shared/components/table/LoadReportTable'

const VIEW_ALL_PAGES = [{ name: 'Broad', downloadName: 'All', path: 'all' }]

const COLUMNS = [
  { name: 'data_type' },
  { name: 'date_data_generation' },
  { name: 'phenotype_description' },
  { name: 'consanguinity' },
  { name: 'analysis_status', content: 'analysis_status' },
  { name: 'solve_state' },
  { name: 'genes' },
  { name: 'inheritance_model' },
  { name: 'disease_id' },
  { name: 'disease_description' },
  { name: 'individual_count', content: '# individuals' },
  { name: 'family_structure' },
  { name: 'proband_id' },
  { name: 'paternal_id' },
  { name: 'maternal_id' },
  { name: 'other_individual_ids' },
  { name: 'collaborator' },
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

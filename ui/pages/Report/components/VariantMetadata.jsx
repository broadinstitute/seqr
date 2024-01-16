import React from 'react'

import LoadReportTable from 'shared/components/table/LoadReportTable'
import { VARIANT_METADATA_COLUMNS } from 'shared/utils/constants'

const VIEW_ALL_PAGES = [
  { name: 'GREGoR', downloadName: 'GREGoR', path: 'gregor' },
  { name: 'Broad', downloadName: 'All', path: 'all' },
]

const COLUMNS = [
  { name: 'participant_id' },
  ...VARIANT_METADATA_COLUMNS.slice(0, -1),
  { name: 'allele_balance_or_heteroplasmy_percentage' },
  { name: 'ClinGen allele ID', format: ({ clinvar }) => clinvar?.alleleId },
  { name: 'ClinVar Clinical Significance', format: ({ clinvar }) => clinvar?.clinicalSignificance },
  { name: 'ClinVar gold star', format: ({ clinvar }) => clinvar?.goldStars },
  { name: 'known_condition_name' },
  { name: 'condition_id' },
  { name: 'condition_inheritance' },
  { name: 'phenotype_contribution' },
  { name: 'additional_family_members_with_variant' },
  { name: 'method_of_discovery' },
  { name: 'Submitted to MME', format: ({ MME }) => (MME ? 'Yes' : 'No') },
  ...VARIANT_METADATA_COLUMNS.slice(-1),
]

const FamilyMetadata = props => (
  <LoadReportTable
    columns={COLUMNS}
    viewAllPages={VIEW_ALL_PAGES}
    urlBase="report/variant_metadata"
    idField="genetic_findings_id"
    fileName="Variant_Metadata"
    {...props}
  />
)

export default FamilyMetadata

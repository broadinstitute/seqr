import React from 'react'

import { clinvarSignificance, VARIANT_METADATA_COLUMNS } from 'shared/utils/constants'
import LoadReportTable from './LoadReportTable'

const COLUMNS = [
  { name: 'participant_id' },
  ...VARIANT_METADATA_COLUMNS.slice(0, -1),
  { name: 'allele_balance_or_heteroplasmy_percentage' },
  { name: 'Clinvar allele ID', format: ({ clinvar }) => clinvar?.alleleId },
  { name: 'ClinVar Clinical Significance', format: ({ clinvar }) => clinvarSignificance(clinvar).pathogenicity },
  { name: 'ClinVar gold star', format: ({ clinvar }) => clinvar?.goldStars },
  { name: 'known_condition_name' },
  { name: 'condition_id' },
  { name: 'condition_inheritance' },
  { name: 'phenotype_contribution' },
  { name: 'additional_family_members_with_variant' },
  { name: 'method_of_discovery' },
  { name: 'Submitted to MME', format: ({ MME }) => (MME ? 'Yes' : 'No') },
  ...VARIANT_METADATA_COLUMNS.slice(-1),
  { name: 'tags', format: ({ tags }) => (tags || []).join('; ') },
]

const FamilyMetadata = props => (
  <LoadReportTable
    columns={COLUMNS}
    urlPath="variant_metadata"
    idField="genetic_findings_id"
    {...props}
  />
)

export default FamilyMetadata

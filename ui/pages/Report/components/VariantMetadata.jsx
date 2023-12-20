import React from 'react'

import LoadReportTable from 'shared/components/table/LoadReportTable'

const VIEW_ALL_PAGES = [
  { name: 'GREGoR', downloadName: 'GREGoR', path: 'gregor'},
  { name: 'Broad', downloadName: 'All', path: 'all' },
]

const COLUMNS = [
  { name: 'participant_id' },
  { name: 'genetic_findings_id' },
  { name: 'variant_reference_assembly' },
  { name: 'chrom' },
  { name: 'pos' },
  { name: 'ref' },
  { name: 'alt' },
  { name: 'gene' },
  { name: 'seqr_chosen_consequence' },
  { name: 'transcript' },
  { name: 'hgvsc' },
  { name: 'hgvsp' },
  { name: 'allele_balance_or_heteroplasmy_percentage' },
  { name: 'zygosity' },
  { name: 'sv_name' },
  { name: 'svType', content: 'sv_type' },
  { name: 'variant_inheritance' },
  { name: 'ClinGen allele ID', format: ({ clinvar }) => clinvar?.alleleId },
  { name: 'ClinVar Clinical Significance', format: ({ clinvar }) => clinvar?.clinicalSignificance },
  { name: 'ClinVar gold star', format: ({ clinvar }) => clinvar?.goldStars },
  { name: 'Submitted to MME', format: ({ MME }) => (MME ? 'Yes' : 'No') },
  { name: 'gene_known_for_phenotype' },
  { name: 'known_condition_name' },
  { name: 'condition_id' },
  { name: 'condition_inheritance' },
  { name: 'phenotype_contribution' },
  { name: 'additional_family_members_with_variant' },
  { name: 'method_of_discovery' },
  { name: 'notes' },
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

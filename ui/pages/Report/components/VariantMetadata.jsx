import React from 'react'

import LoadReportTable from 'shared/components/table/LoadReportTable'

const VIEW_ALL_PAGES = [{ name: 'Broad', downloadName: 'All', path: 'all' }]

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
  { name: 'zygosity' },
  { name: 'sv_name' },
  { name: 'sv_type' },
  { name: 'variant_inheritance' },
  { name: 'ClinGen_allele_ID' },
  { name: 'ClinVar Clinical Significance' },
  { name: 'ClinVar gold star' },
  { name: 'Submitted to MME' },
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

import React from 'react'
import { Link } from 'react-router-dom'

import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { parseHgvs } from 'shared/components/panel/variants/Annotations'
import {
  INDIVIDUAL_FIELD_CONFIGS,
  INDIVIDUAL_HPO_EXPORT_DATA,
  FAMILY_FIELD_CODED_PHENOTYPE,
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
} from 'shared/utils/constants'

const PROJECT_ID_FIELD = 'Project_ID'

const FORMAT_FIELDS = {
  [PROJECT_ID_FIELD]: row =>
    <Link to={`/project/${row.projectGuid}/project_page`} target="_blank">{row[PROJECT_ID_FIELD]}</Link>,
  [FAMILY_FIELD_ID]: row =>
    <Link to={`/project/${row.projectGuid}/family_page/${row.familyGuid}`} target="_blank">{row[FAMILY_FIELD_ID]}</Link>,
}

const PROJECT_ID_COL = { name: PROJECT_ID_FIELD }
const CODED_PHENPOTYPE_COL = { name: FAMILY_FIELD_CODED_PHENOTYPE, content: 'Phenotype', style: { minWidth: '200px' } }

const INDIVIDUAL_COLUMNS = [
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
].map((field) => {
  const { label, format } = INDIVIDUAL_FIELD_CONFIGS[field]
  return {
    name: field,
    content: label.replace(' ', '_'),
    format: format ? row => format(row[field]) : null,
  }
})

const HPO_COLUMNS = INDIVIDUAL_HPO_EXPORT_DATA.map(({ field, header, format }) => (
  {
    name: header,
    content: header.replace(/[()]/g, '').split(' ').map(word => word[0].toUpperCase() + word.slice(1)).join('_'),
    format: row => format(row[field]),
    style: { minWidth: '400px' },
  }
))

export const CORE_ANVIL_COLUMNS = [
  PROJECT_ID_COL, ...INDIVIDUAL_COLUMNS, CODED_PHENPOTYPE_COL, ...HPO_COLUMNS,
].map(({ name, content, format, ...props }) => ({
  name,
  content: content || name,
  format: format || FORMAT_FIELDS[name],
  noFormatExport: Boolean(FORMAT_FIELDS[name]),
  ...props,
}))

export const VARIANT_ANVIL_COLUMNS = [
  'Gene',
  'Zygosity',
  'Chrom',
  'Pos',
  'Ref',
  'Alt',
  'hgvsc',
  'hgvsp',
  'Transcript',
]

export const VARIANT_ANVIL_COLUMN_FORMATS = {
  hgvsc: parseHgvs,
  hgvsp: parseHgvs,
}

const formatT0 = row => new Date(row.t0).toISOString().slice(0, 10)
const pedigreeImageFamily = row => ({ pedigreeImage: row.extras_pedigree_url })
const formatFamilySummary = row =>
  <div>
    <PedigreeImagePanel family={pedigreeImageFamily(row)} disablePedigreeZoom compact />
    <Link to={`/project/${row.project_guid}/family_page/${row.family_guid}`} target="_blank">{row.family_id}</Link>
    {row.extras_variant_tag_list &&
      <div>{row.extras_variant_tag_list.map(tag => <div><small>{tag}</small></div>)}</div>
    }
  </div>


export const DISCOVERY_SHEET_COLUMNS = [
  { name: 't0', content: 'T0', format: formatT0, style: { minWidth: '100px' } },
  { name: 'family_id', content: 'Family ID', format: formatFamilySummary, noFormatExport: true, style: { minWidth: '200px' } },
  { name: 'coded_phenotype', content: 'Phenotype' },
  { name: 'sequencing_approach', content: 'Sequencing Approach' },
  { name: 'sample_source', content: 'Sample Source' },
  { name: 'analysis_complete_status', content: 'Analysis Status' },
  { name: 'expected_inheritance_model', content: 'Expected Inheritance Model' },
  { name: 'actual_inheritance_model', content: 'Actual Inheritance Model' },
  { name: 'n_kindreds', content: '# Kindreds' },
  { name: 'gene_name', content: 'Gene Name' },
  { name: 'novel_mendelian_gene', content: 'Novel Mendelian Gene' },
  { name: 'gene_count', content: 'Gene Count' },
  { name: 'phenotype_class', content: 'Phenotype Class' },
  { name: 'solved', content: 'Solved' },
  { name: 'genome_wide_linkage', content: 'Genome-wide Linkage' },
  { name: 'p_value', content: 'Bonferroni corrected p-value' },
  { name: 'n_kindreds_overlapping_sv_similar_phenotype', content: '# Kindreds w/ Overlapping SV & Similar Phenotype' },
  { name: 'n_unrelated_kindreds_with_causal_variants_in_gene', content: '# Unrelated Kindreds w/ Causal Variants in Gene' },
  { name: 'biochemical_function', content: 'Biochemical Function' },
  { name: 'protein_interaction', content: 'Protein Interaction' },
  { name: 'expression', content: 'Expression' },
  { name: 'patient_cells', content: 'Patient cells' },
  { name: 'non_patient_cell_model', content: 'Non-patient cells' },
  { name: 'animal_model', content: 'Animal model' },
  { name: 'non_human_cell_culture_model', content: 'Non-human Cell culture model' },
  { name: 'rescue', content: 'Rescue' },
  { name: 'omim_number_initial', content: 'OMIM # (initial)' },
  { name: 'omim_number_post_discovery', content: 'OMIM # (post-discovery)' },
  { name: 'connective_tissue', content: 'Abnormality of Connective Tissue' },
  { name: 'voice', content: 'Abnormality of the Voice' },
  { name: 'nervous_system', content: 'Abnormality of the Nervous System' },
  { name: 'breast', content: 'Abnormality of the Breast' },
  { name: 'eye_defects', content: 'Abnormality of the Eye' },
  { name: 'prenatal_development_or_birth', content: 'Abnormality of Prenatal Development or Birth' },
  { name: 'neoplasm', content: 'Neoplasm' },
  { name: 'endocrine_system', content: 'Abnormality of the Endocrine System' },
  { name: 'head_or_neck', content: 'Abnormality of Head or Neck' },
  { name: 'immune_system', content: 'Abnormality of the Immune System' },
  { name: 'growth', content: 'Growth Abnormality' },
  { name: 'limbs', content: 'Abnormality of Limbs' },
  { name: 'thoracic_cavity', content: 'Abnormality of the Thoracic Cavity' },
  { name: 'blood', content: 'Abnormality of Blood and Blood-forming Tissues' },
  { name: 'musculature', content: 'Abnormality of the Musculature' },
  { name: 'cardiovascular_system', content: 'Abnormality of the Cardiovascular System' },
  { name: 'abdomen', content: 'Abnormality of the Abdomen' },
  { name: 'skeletal_system', content: 'Abnormality of the Skeletal System' },
  { name: 'respiratory', content: 'Abnormality of the Respiratory System' },
  { name: 'ear_defects', content: 'Abnormality of the Ear' },
  { name: 'metabolism_homeostasis', content: 'Abnormality of Metabolism / Homeostasis' },
  { name: 'genitourinary_system', content: 'Abnormality of the Genitourinary System' },
  { name: 'integument', content: 'Abnormality of the Integument' },
  { name: 't0_copy', content: 'T0', format: formatT0, style: { minWidth: '100px' } },
  { name: 'months_since_t0', content: 'Months since T0' },
  { name: 'submitted_to_mme', content: 'Submitted to MME (deadline 7 months post T0)' },
  { name: 'posted_publicly', content: 'Posted publicly (deadline 12 months posted T0)' },
  { name: 'komp_early_release', content: 'KOMP Early Release' },
  { name: 'pubmed_ids', content: 'PubMed IDs for gene' },
  { name: 'collaborator', content: 'Collaborator' },
  { name: 'num_individuals_sequenced', content: '# of Individuals Sequenced' },
  { name: 'analysis_summary', content: 'Analysis Summary', style: { minWidth: '800px' } },
]

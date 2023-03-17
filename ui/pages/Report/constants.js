import React from 'react'
import { Link } from 'react-router-dom'

const PROJECT_ID_FIELD = 'project_id'
const FAMILY_FIELD_ID = 'family_id'

export const ALL_PROJECTS_PATH = 'all'
export const GREGOR_PROJECT_PATH = 'gregor'
export const CMG_PROJECT_PATH = 'cmg'

export const CORE_ANVIL_COLUMNS = [
  { name: 'subject_id' },
  {
    name: PROJECT_ID_FIELD,
    format:
      row => <Link to={`/project/${row.project_guid}/project_page`} target="_blank">{row[PROJECT_ID_FIELD]}</Link>,
    noFormatExport: true,
  },
  {
    name: FAMILY_FIELD_ID,
    format:
      row => <Link to={`/project/${row.project_guid}/family_page/${row.family_guid}`} target="_blank">{row[FAMILY_FIELD_ID]}</Link>,
    noFormatExport: true,
  },
  { name: 'pmid_id' },
  { name: 'paternal_id' },
  { name: 'maternal_id' },
  { name: 'proband_relationship' },
  { name: 'sex' },
  { name: 'ancestry' },
  { name: 'phenotype_group' },
  { name: 'disease_id' },
  { name: 'disease_description' },
  { name: 'affected_status' },
  { name: 'congenital_status' },
  { name: 'hpo_present', style: { minWidth: '400px' } },
  { name: 'hpo_absent', style: { minWidth: '400px' } },
  { name: 'phenotype_description', style: { minWidth: '200px' } },
  { name: 'solve_state' },
  { name: 'MME' },
  { name: 'sample_id' },
  { name: 'data_type' },
  { name: 'date_data_generation' },
  { name: 'consanguinity' },
  { name: 'family_history' },
]

export const AIRTABLE_ANVIL_COLUMNS = [
  { name: 'dbgap_submission' },
  { name: 'dbgap_study_id' },
  { name: 'dbgap_subject_id' },
  { name: 'multiple_datasets' },
  { name: 'dbgap_sample_id' },
  { name: 'sample_provider' },
]

export const VARIANT_ANVIL_COLUMNS = [
  'Gene',
  'Gene_Class',
  'novel_mendelian_gene',
  'phenotype_class',
  'inheritance_description',
  'Zygosity',
  'Chrom',
  'Pos',
  'Ref',
  'Alt',
  'hgvsc',
  'hgvsp',
  'Transcript',
  'sv_name',
  'sv_type',
  'discovery_notes',
]

const formatT0 = row => new Date(row.t0).toISOString().slice(0, 10)
const formatFamilySummary = row => (
  <div>
    <Link to={`/project/${row.project_guid}/family_page/${row.family_guid}`} target="_blank">{row.family_id}</Link>
    {row.extras_variant_tag_list &&
      <div>{row.extras_variant_tag_list.map(tag => <div><small>{tag}</small></div>)}</div>}
  </div>
)

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

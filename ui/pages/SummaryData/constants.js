import React from 'react'
import { Link } from 'react-router-dom'

import { successStoryTypeDisplay } from 'shared/utils/constants'

export const ALL_PROJECTS_PATH = 'all'

const formatIDLink =
  row => <Link to={`/project/${row.project_guid}/family_page/${row.family_guid}`} target="_blank">{row.family_id}</Link>

const formatSuccessStoryTypes =
  row => row.success_story_types && row.success_story_types.map(tag => <div>{successStoryTypeDisplay(tag)}</div>)

const formatDiscoveryTags = row => row.extras_variant_tag_list &&
  <div>{row.extras_variant_tag_list.map(tag => <div><small>{tag}</small></div>)}</div>

export const SUCCESS_STORY_COLUMNS = [
  { name: 'family_id', content: 'Family ID', format: formatIDLink, noFormatExport: true, style: { minWidth: '200px' } },
  { name: 'success_story_types', content: 'Success Story Types', format: formatSuccessStoryTypes, noFormatExport: true, style: { minWidth: '300px' } },
  { name: 'success_story', content: 'Success Story', style: { minWidth: '564px' } },
  { name: 'discovery_tags', content: 'Discovery Tags', format: formatDiscoveryTags, noFormatExport: true, style: { minWidth: '400px' } },
]

const PROJECT_ID_FIELD = 'project_id'
const FAMILY_FIELD_ID = 'family_id'

export const CORE_METADATA_COLUMNS = [
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

export const AIRTABLE_METADATA_COLUMNS = [
  { name: 'dbgap_submission' },
  { name: 'dbgap_study_id' },
  { name: 'dbgap_subject_id' },
  { name: 'multiple_datasets' },
  { name: 'dbgap_sample_id' },
  { name: 'sample_provider' },
]

export const VARIANT_METADATA_COLUMNS = [
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

import React from 'react'

import { BaseSemanticInput, BooleanCheckbox } from 'shared/components/form/Inputs'
import { FAMILY_ANALYSIS_STATUS_LOOKUP, VARIANT_METADATA_COLUMNS } from 'shared/utils/constants'
import LoadReportTable from './LoadReportTable'

const FIELDS = [
  {
    name: 'loadedBefore',
    label: 'Loaded Before',
    inline: true,
    component: BaseSemanticInput,
    inputType: 'Input',
    type: 'date',
  },
]

const AIRTABLE_FIELDS = [
  ...FIELDS,
  {
    name: 'includeAirtable',
    label: 'Include Airtable Columns',
    inline: true,
    component: BooleanCheckbox,
  },
]

const CORE_COLUMNS = [
  { name: 'participant_id', secondaryExportColumn: 'individual_guid' },
  { name: 'pmid_id' },
  { name: 'paternal_id', secondaryExportColumn: 'paternal_guid' },
  { name: 'maternal_id', secondaryExportColumn: 'maternal_guid' },
  { name: 'proband_relationship' },
  { name: 'sex' },
  { name: 'ancestry' },
  { name: 'condition_id' },
  { name: 'known_condition_name', secondaryExportColumn: 'disorders' },
  { name: 'affected_status' },
  { name: 'hpo_present', style: { minWidth: '400px' } },
  { name: 'hpo_absent', style: { minWidth: '400px' } },
  { name: 'phenotype_description', style: { minWidth: '200px' } },
  { name: 'analysis_groups' },
  {
    name: 'analysisStatus',
    content: 'analysis_status',
    format: ({ analysisStatus }) => FAMILY_ANALYSIS_STATUS_LOOKUP[analysisStatus]?.name,
  },
  { name: 'solve_status' },
  { name: 'MME' },
  { name: 'data_type' },
  { name: 'date_data_generation', secondaryExportColumn: 'filter_flags' },
  { name: 'consanguinity' },
  { name: 'family_history' },
]

const AIRTABLE_DBGAP_SUBMISSION_FIELD = 'dbgap_submission'
const AIRTABLE_COLUMNS = [
  { name: AIRTABLE_DBGAP_SUBMISSION_FIELD },
  { name: 'dbgap_study_id' },
  { name: 'dbgap_subject_id' },
  { name: 'multiple_datasets' },
  { name: 'dbgap_sample_id' },
  { name: 'sample_provider' },
]

const getColumns = (data) => {
  const maxSavedVariants = Math.max(1, ...(data || []).map(row => row.num_saved_variants))
  const hasAirtable = data && data[0] && data[0][AIRTABLE_DBGAP_SUBMISSION_FIELD]
  return [...CORE_COLUMNS, ...(hasAirtable ? AIRTABLE_COLUMNS : [])].concat(
    ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_METADATA_COLUMNS.map(
      ({ name, format, fieldName, ...col }) => ({
        name: `${name}-${i + 1}`,
        secondaryExportColumn: name === 'gene' ? `gene_id-${i + 1}` : null,
        format: format ? row => format({ [fieldName]: row[`${fieldName}-${i + 1}`] }) : null,
        ...col,
      }),
    )),
  )
}

const IndividualMetadata = props => (
  <LoadReportTable
    getColumns={getColumns}
    allQueryFields={AIRTABLE_FIELDS}
    queryFields={FIELDS}
    urlPath="individual_metadata"
    idField="participant_id"
    {...props}
  />
)

export default IndividualMetadata

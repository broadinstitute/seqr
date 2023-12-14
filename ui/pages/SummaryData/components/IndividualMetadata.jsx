import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import { BaseSemanticInput, BooleanCheckbox } from 'shared/components/form/Inputs'
import LoadReportTable from 'shared/components/table/LoadReportTable'
import { FAMILY_ANALYSIS_STATUS_LOOKUP } from 'shared/utils/constants'

const ALL_PROJECTS_PATH = 'all'
const GREGOR_PROJECT_PATH = 'gregor'

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
  { name: 'subject_id', content: 'participant_id', secondaryExportColumn: 'individual_guid' },
  { name: 'pmid_id' },
  { name: 'paternal_id', secondaryExportColumn: 'paternal_guid' },
  { name: 'maternal_id', secondaryExportColumn: 'maternal_guid' },
  { name: 'proband_relationship' },
  { name: 'sex' },
  { name: 'ancestry' },
  { name: 'disease_id' },
  { name: 'disease_description', secondaryExportColumn: 'disorders' },
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
  { name: 'solve_state' },
  { name: 'MME' },
  { name: 'sample_id' }, // TODO
  { name: 'data_type' },
  { name: 'date_data_generation', secondaryExportColumn: 'filter_flags' },
  { name: 'consanguinity' },
  { name: 'family_history' },
  { name: 'notes' },
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

const GENE_COL = 'Gene'
const VARIANT_COLUMNS = [
  GENE_COL,
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

const ANALYST_VIEW_ALL_PAGES = [
  { name: 'GREGoR', downloadName: 'All_GREGoR_Projects', path: GREGOR_PROJECT_PATH },
  { name: 'Broad', downloadName: 'All_AnVIL_Projects', path: ALL_PROJECTS_PATH },
]
const VIEW_ALL_PAGES = [{ name: 'my', downloadName: 'All_Projects', path: ALL_PROJECTS_PATH }]

const getColumns = (data) => {
  const maxSavedVariants = Math.max(1, ...(data || []).map(row => row.num_saved_variants))
  const hasAirtable = data && data[0] && data[0][AIRTABLE_DBGAP_SUBMISSION_FIELD]
  return [...CORE_COLUMNS, ...(hasAirtable ? AIRTABLE_COLUMNS : [])].concat(
    ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_COLUMNS.map(
      col => ({ name: `${col}-${i + 1}`, secondaryExportColumn: col === GENE_COL ? `gene_id-${i + 1}` : null }),
    )),
  )
}

const mapStateToProps = (state, ownProps) => {
  const user = getUser(state)
  return {
    getColumns,
    queryFields: (user.isAnalyst && ownProps.match.params.projectGuid !== ALL_PROJECTS_PATH) ? AIRTABLE_FIELDS : FIELDS,
    viewAllPages: (user.isAnalyst ? ANALYST_VIEW_ALL_PAGES : VIEW_ALL_PAGES),
    urlBase: 'summary_data/individual_metadata',
    idField: 'subject_id',
    fileName: 'Metadata',
  }
}

export default connect(mapStateToProps)(LoadReportTable)

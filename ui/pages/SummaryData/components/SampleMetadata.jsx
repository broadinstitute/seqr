import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import StateDataLoader from 'shared/components/StateDataLoader'
import { InlineHeader, ActiveDisabledNavLink } from 'shared/components/StyledComponents'
import { BaseSemanticInput, BooleanCheckbox } from 'shared/components/form/Inputs'

const ALL_PROJECTS_PATH = 'all'
const GREGOR_PROJECT_PATH = 'gregor'

const FILENAME_LOOKUP = {
  [ALL_PROJECTS_PATH]: 'All_AnVIL_Projects',
  [GREGOR_PROJECT_PATH]: 'All_GREGoR_Projects',
}

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

const PROJECT_ID_FIELD = 'project_id'
const FAMILY_FIELD_ID = 'family_id'

const CORE_COLUMNS = [
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

const AIRTABLE_DBGAP_SUBMISSION_FIELD = 'dbgap_submission'
const AIRTABLE_COLUMNS = [
  { name: AIRTABLE_DBGAP_SUBMISSION_FIELD },
  { name: 'dbgap_study_id' },
  { name: 'dbgap_subject_id' },
  { name: 'multiple_datasets' },
  { name: 'dbgap_sample_id' },
  { name: 'sample_provider' },
]

const VARIANT_COLUMNS = [
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

const ANALYST_VIEW_ALL_PAGES = [{ name: 'GREGoR', path: GREGOR_PROJECT_PATH }, { name: 'Broad', path: ALL_PROJECTS_PATH }]
const VIEW_ALL_PAGES = [{ name: 'my', path: ALL_PROJECTS_PATH }]

const SEARCH_CATEGORIES = ['projects']

const getResultHref = result => `/summary_data/sample_metadata/${result.key}`

const getColumns = (data) => {
  const maxSavedVariants = Math.max(1, ...(data || []).map(row => row.num_saved_variants))
  const hasAirtable = data && data[0] && data[0][AIRTABLE_DBGAP_SUBMISSION_FIELD]
  return [...CORE_COLUMNS, ...(hasAirtable ? AIRTABLE_COLUMNS : [])].concat(
    ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_COLUMNS.map(col => ({ name: `${col}-${i + 1}` }))),
  ).map(({ name, ...props }) => ({ name, content: name, ...props }))
}

const SampleMetadata = React.memo(({ projectGuid, queryForm, data, user }) => (
  <div>
    <InlineHeader size="medium" content="Project:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref}
    />
    {(user.isAnalyst ? ANALYST_VIEW_ALL_PAGES : VIEW_ALL_PAGES).map(({ name, path }) => (
      <span key={path}>
        &nbsp; or &nbsp;
        <ActiveDisabledNavLink to={`/summary_data/sample_metadata/${path}`}>{`view all ${name} projects`}</ActiveDisabledNavLink>
      </span>
    ))}
    <HorizontalSpacer width={20} />
    {queryForm}
    <DataTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={`${FILENAME_LOOKUP[projectGuid] || (data?.length && data[0].project_id.replace(/ /g, '_'))}_${new Date().toISOString().slice(0, 10)}_Metadata`}
      idField="subject_id"
      defaultSortColumn="family_id"
      emptyContent={projectGuid ? '0 cases found' : 'Select a project to view data'}
      data={data}
      columns={getColumns(data)}
      rowsPerPage={100}
    />
  </div>
))

SampleMetadata.propTypes = {
  data: PropTypes.arrayOf(PropTypes.object),
  projectGuid: PropTypes.string,
  queryForm: PropTypes.node,
  user: PropTypes.object,
}

const parseResponse = ({ rows }) => ({ data: rows })

const LoadedSampleMetadata = ({ match, user }) => (
  <StateDataLoader
    url={match.params.projectGuid ? `/api/summary_data/sample_metadata/${match.params.projectGuid}` : ''}
    parseResponse={parseResponse}
    queryFields={(user.isAnalyst && match.params.projectGuid !== ALL_PROJECTS_PATH) ? AIRTABLE_FIELDS : FIELDS}
    childComponent={SampleMetadata}
    projectGuid={match.params.projectGuid}
    user={user}
  />
)

LoadedSampleMetadata.propTypes = {
  match: PropTypes.object,
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(LoadedSampleMetadata)

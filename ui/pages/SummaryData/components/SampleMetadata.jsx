import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'
import FormWrapper from 'shared/components/form/FormWrapper'
import { BaseSemanticInput, BooleanCheckbox } from 'shared/components/form/Inputs'
import { ALL_PROJECTS_PATH, GREGOR_PROJECT_PATH } from '../constants'
import { loadSampleMetadata } from '../reducers'
import { getSampleMetadataLoading, getSampleMetadataLoadingError, getSampleMetadataRows, getSampleMetadataColumns } from '../selectors'

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
  {
    name: 'omitAirtable',
    label: 'Skip Airtable Columns',
    inline: true,
    component: BooleanCheckbox,
  },
]

const VIEW_ALL_PAGES = [{ name: 'GREGoR', path: GREGOR_PROJECT_PATH }, { name: 'Broad', path: ALL_PROJECTS_PATH }]

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const LOADING_PROPS = { inline: true }

const getResultHref = result => `/summary_data/sample_metadata/${result.key}`

const SampleMetadata = React.memo(({ match, data, columns, loading, load, loadingError }) => (
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Project:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref}
    />
    {VIEW_ALL_PAGES.map(({ name, path }) => (
      <span>
        &nbsp; or &nbsp;
        <NavLink to={`/summary_data/sample_metadata/${path}`} activeStyle={ACTIVE_LINK_STYLE}>{`view all ${name} projects`}</NavLink>
      </span>
    ))}
    <HorizontalSpacer width={20} />
    <FormWrapper
      onSubmit={load}
      fields={FIELDS}
      noModal
      inline
      submitOnChange
    />
    <DataTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={`${FILENAME_LOOKUP[match.params.projectGuid] || (data.length && data[0].project_id.replace(/ /g, '_'))}_${new Date().toISOString().slice(0, 10)}_Metadata`}
      idField="subject_id"
      defaultSortColumn="family_id"
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={columns}
      loadingProps={LOADING_PROPS}
      rowsPerPage={100}
    />
  </DataLoader>
))

SampleMetadata.propTypes = {
  match: PropTypes.object,
  data: PropTypes.arrayOf(PropTypes.object),
  columns: PropTypes.arrayOf(PropTypes.object),
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  data: getSampleMetadataRows(state),
  columns: getSampleMetadataColumns(state, ownProps),
  loading: getSampleMetadataLoading(state),
  loadingError: getSampleMetadataLoadingError(state),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  load: (values) => {
    dispatch(loadSampleMetadata(ownProps.match.params.projectGuid, typeof values === 'object' ? values : {}))
  },
})

export default connect(mapStateToProps, mapDispatchToProps)(SampleMetadata)

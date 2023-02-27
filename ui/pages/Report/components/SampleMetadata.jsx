import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import FormWrapper from 'shared/components/form/FormWrapper'
import { BaseSemanticInput, BooleanCheckbox } from 'shared/components/form/Inputs'
import { ALL_PROJECTS_PATH, GREGOR_PROJECT_PATH } from '../constants'
import { loadSampleMetadata } from '../reducers'
import { getSampleMetadataLoading, getSampleMetadataLoadingError, getSampleMetadataRows, getSampleMetadataColumns } from '../selectors'
import BaseReport from './BaseReport'

const FILENAME_LOOKUP = {
  [ALL_PROJECTS_PATH]: 'All_AnVIL_Projects',
  [GREGOR_PROJECT_PATH]: 'All_GREGoR_Projects',
}

const getDownloadFilename = (projectGuid, data) => {
  const projectName = FILENAME_LOOKUP[projectGuid] || (data.length && data[0].project_id.replace(/ /g, '_'))
  return `${projectName}_${new Date().toISOString().slice(0, 10)}_Metadata`
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

const SampleMetadataFilters = React.memo(({ load }) => (
  <FormWrapper
    onSubmit={load}
    fields={FIELDS}
    noModal
    inline
    submitOnChange
  />
))

SampleMetadataFilters.propTypes = {
  load: PropTypes.func,
}

const VIEW_ALL_PAGES = [{ name: 'GREGoR', path: GREGOR_PROJECT_PATH }, { name: 'Broad', path: ALL_PROJECTS_PATH }]

const SampleMetadata = React.memo(props => (
  <BaseReport
    page="sample_metadata"
    viewAllPages={VIEW_ALL_PAGES}
    idField="subject_id"
    defaultSortColumn="family_id"
    getDownloadFilename={getDownloadFilename}
    filters={<SampleMetadataFilters {...props} />}
    rowsPerPage={100}
    {...props}
  />
))

SampleMetadata.propTypes = {
  match: PropTypes.object,
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

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { loadSampleMetadata } from '../reducers'
import { getSampleMetadataLoading, getSampleMetadataLoadingError, getSampleMetadataRows, getSampleMetadataColumns } from '../selectors'
import BaseReport from './BaseReport'

const getDownloadFilename = (projectGuid, data) => {
  const projectName = projectGuid && projectGuid !== 'all' && data.length && data[0].project_id.replace(/ /g, '_')
  return `${projectName || 'All_AnVIL_Projects'}_${new Date().toISOString().slice(0, 10)}_Metadata`
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

const SampleMetadataFilters = React.memo(({ load, match }) =>
  <ReduxFormWrapper
    onSubmit={values => load(match.params.projectGuid, values)}
    form="sampleMetadataFilters"
    fields={FIELDS}
    noModal
    inline
    submitOnChange
  />,
)

SampleMetadataFilters.propTypes = {
  match: PropTypes.object,
  load: PropTypes.func,
}

const SampleMetadata = React.memo(props =>
  <BaseReport
    page="sample_metadata"
    viewAllCategory="CMG"
    idField="subject_id"
    defaultSortColumn="family_id"
    getDownloadFilename={getDownloadFilename}
    filters={<SampleMetadataFilters {...props} />}
    rowsPerPage={100}
    {...props}
  />,
)

SampleMetadata.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  columns: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: getSampleMetadataRows(state),
  columns: getSampleMetadataColumns(state),
  loading: getSampleMetadataLoading(state),
  loadingError: getSampleMetadataLoadingError(state),
})

const mapDispatchToProps = {
  load: loadSampleMetadata,
}

export default connect(mapStateToProps, mapDispatchToProps)(SampleMetadata)

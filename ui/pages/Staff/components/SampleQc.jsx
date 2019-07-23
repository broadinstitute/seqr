import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import FileUploadField, { validateUploadedFile, warnUploadedFile } from 'shared/components/form/XHRUploaderField'

import { uploadQcPipelineOutput } from '../reducers'


const UPLOAD_FIELDS = [
  {
    name: 'file',
    component: FileUploadField,
    clearTimeOut: 0,
    auto: true,
    required: true,
    validate: validateUploadedFile,
    warn: warnUploadedFile,
    dropzoneLabel: 'Upload QC Pipeline Output',
    url: '/api/staff/upload_qc_pipeline_output',
  },
]

const SampleQcUpload = ({ onSubmit }) =>
  <Grid>
    <Grid.Column width={4} />
    <Grid.Column width={8}>
      <ReduxFormWrapper
        form="sampleQc"
        onSubmit={onSubmit}
        showErrorPanel
        liveValidate
        fields={UPLOAD_FIELDS}
        noModal
        successMessage="QC info successfully added"
      />
    </Grid.Column>
    <Grid.Column width={4} />
  </Grid>

SampleQcUpload.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: uploadQcPipelineOutput,
}

export default connect(null, mapDispatchToProps)(SampleQcUpload)

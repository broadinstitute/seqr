import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Message } from 'semantic-ui-react'

import ReduxFormWrapper, { validators } from 'shared/components/form/ReduxFormWrapper'

import { getQcUploadStats } from '../selectors'
import { uploadQcPipelineOutput } from '../reducers'

const UPLOAD_FIELDS = [
  {
    name: 'file',
    label: 'QC Pipeline Output File Path',
    placeholder: 'gs:// Google bucket path',
    validate: validators.required,
  },
]

const SampleQcUpload = React.memo(({ qcUploadStats, onSubmit }) => (
  <Grid>
    <Grid.Row>
      <Grid.Column width={4} />
      <Grid.Column width={8}>
        <ReduxFormWrapper
          form="sampleQc"
          onSubmit={onSubmit}
          fields={UPLOAD_FIELDS}
          noModal
        />
      </Grid.Column>
      <Grid.Column width={4} />
    </Grid.Row>
    <Grid.Row>
      <Grid.Column width={4} />
      <Grid.Column width={8}>
        {qcUploadStats.info && <Message info list={qcUploadStats.info} />}
        {qcUploadStats.warnings && <Message warning list={qcUploadStats.warnings} />}
      </Grid.Column>
      <Grid.Column width={4} />
    </Grid.Row>
  </Grid>
))

SampleQcUpload.propTypes = {
  qcUploadStats: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  qcUploadStats: getQcUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadQcPipelineOutput,
}

export default connect(mapStateToProps, mapDispatchToProps)(SampleQcUpload)

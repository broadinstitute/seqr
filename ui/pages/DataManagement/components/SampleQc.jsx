import { connect } from 'react-redux'

import { validators } from 'shared/components/form/ReduxFormWrapper'

import { getQcUploadStats } from '../selectors'
import { uploadQcPipelineOutput } from '../reducers'
import UploadFormPage from './UploadFormPage'

const UPLOAD_FIELDS = [
  {
    name: 'file',
    label: 'QC Pipeline Output File Path',
    placeholder: 'gs:// Google bucket path',
    validate: validators.required,
  },
]

const mapStateToProps = state => ({
  formId: 'sampleQc',
  fields: UPLOAD_FIELDS,
  uploadStats: getQcUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadQcPipelineOutput,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

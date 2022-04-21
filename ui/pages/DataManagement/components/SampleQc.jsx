import { connect } from 'react-redux'

import { validators } from 'shared/components/form/FormHelpers'
import UploadFormPage from 'shared/components/page/UploadFormPage'

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

const mapStateToProps = state => ({
  fields: UPLOAD_FIELDS,
  uploadStats: getQcUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadQcPipelineOutput,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

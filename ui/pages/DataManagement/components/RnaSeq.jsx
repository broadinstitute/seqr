import { connect } from 'react-redux'

import FileUploadField, { validateUploadedFile } from 'shared/components/form/XHRUploaderField'

import { getRnaSeqUploadStats } from '../selectors'
import { uploadRnaSeq } from '../reducers'
import UploadFormPage from './UploadFormPage'

const mapStateToProps = state => ({
  formId: 'rnaSeq',
  fields: [
    {
      name: 'file',
      component: FileUploadField,
      dropzoneLabel: 'Drag-drop or click here to upload RNA-Seq Outlier Data',
      validate: validateUploadedFile,
    },
  ],
  uploadStats: getRnaSeqUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadRnaSeq,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

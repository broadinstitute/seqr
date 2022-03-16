import { connect } from 'react-redux'

import FileUploadField, { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import { BooleanCheckbox } from 'shared/components/form/Inputs'

import { getRnaSeqUploadStats } from '../selectors'
import { uploadRnaSeq } from '../reducers'
import UploadFormPage from './UploadFormPage'

const mapStateToProps = state => ({
  fields: [
    {
      name: 'file',
      component: FileUploadField,
      dropzoneLabel: 'Drag-drop or click here to upload RNA-Seq Outlier Data',
      validate: validateUploadedFile,
      url: '/api/data_management/upload_rna_seq',
    },
    {
      name: 'mappingFile',
      component: FileUploadField,
      dropzoneLabel: 'Drag-drop or click here to upload an optional file that maps Sample Ids (column 1) to their corresponding Seqr Individual Ids (column 2)',
    },
    {
      name: 'ignoreExtraSamples',
      component: BooleanCheckbox,
      label: 'Ignore extra samples',
    },
  ],
  uploadStats: getRnaSeqUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadRnaSeq,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

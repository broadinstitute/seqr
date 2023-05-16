import { connect } from 'react-redux'

import { validators } from 'shared/components/form/FormHelpers'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import { BooleanCheckbox, Select } from 'shared/components/form/Inputs'
import UploadFormPage from 'shared/components/page/UploadFormPage'

import { getRnaSeqUploadStats } from '../selectors'
import { uploadRnaSeq } from '../reducers'

const mapStateToProps = state => ({
  fields: [
    {
      name: 'file',
      label: 'RNA-seq data',
      placeholder: 'gs:// Google bucket path',
      validate: validators.required,
    },
    {
      name: 'dataType',
      label: 'Data Type',
      component: Select,
      options: ['Outlier', 'TPM', 'Splice Outlier'].map(text => ({ text, value: text.toLowerCase().replace(' ', '_') })),
      validate: validators.required,
    },
    {
      name: 'ignoreExtraSamples',
      component: BooleanCheckbox,
      label: 'Ignore extra samples',
    },
    {
      name: 'mappingFile',
      component: FileUploadField,
      dropzoneLabel: 'Drag-drop or click here to upload an optional file that maps Sample Ids (column 1) to their corresponding Seqr Individual Ids (column 2)',
    },
  ],
  uploadStats: getRnaSeqUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadRnaSeq,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

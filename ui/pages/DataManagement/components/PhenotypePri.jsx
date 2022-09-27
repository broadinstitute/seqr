import { connect } from 'react-redux'

import { validators } from 'shared/components/form/FormHelpers'
import { BooleanCheckbox } from 'shared/components/form/Inputs'
import UploadFormPage from 'shared/components/page/UploadFormPage'

import { getPhenoPriUploadStats } from '../selectors'
import { uploadPhenoPri } from '../reducers'

const mapStateToProps = state => ({
  fields: [
    {
      name: 'file',
      label: 'Phenotype-based prioritization data (.tsv)',
      placeholder: 'gs:// Google bucket path',
      validate: validators.required,
    },
    {
      name: 'ignoreExtraSamples',
      component: BooleanCheckbox,
      label: 'Ignore extra samples',
    },
  ],
  uploadStats: getPhenoPriUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadPhenoPri,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

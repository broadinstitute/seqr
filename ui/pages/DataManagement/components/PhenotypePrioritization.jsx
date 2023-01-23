import { connect } from 'react-redux'

import { validators } from 'shared/components/form/FormHelpers'
import UploadFormPage from 'shared/components/page/UploadFormPage'

import { getPhePriUploadStats } from '../selectors'
import { uploadPhenotypePrioritization } from '../reducers'

const FIELDS = [
  {
    name: 'file',
    label: 'Phenotype-based prioritization data (.tsv)',
    placeholder: 'gs:// Google bucket path',
    validate: validators.required,
  },
]

const mapStateToProps = state => ({
  fields: FIELDS,
  uploadStats: getPhePriUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadPhenotypePrioritization,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

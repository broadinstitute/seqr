import { connect } from 'react-redux'

import UploadFormPage from 'shared/components/page/UploadFormPage'
import { LOAD_RNA_FIELDS } from 'shared/utils/constants'

import { getRnaSeqUploadStats } from '../selectors'
import { uploadRnaSeq } from '../reducers'

const mapStateToProps = state => ({
  fields: LOAD_RNA_FIELDS,
  uploadStats: getRnaSeqUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: uploadRnaSeq,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

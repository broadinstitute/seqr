import { connect } from 'react-redux'

import { UPLOAD_IGV_FIELD } from 'shared/components/form/IGVUploadField'
import UploadFormPage from 'shared/components/page/UploadFormPage'

import { getIgvUploadStats } from '../selectors'
import { addIgv } from '../reducers'

const mapStateToProps = state => ({
  fields: [UPLOAD_IGV_FIELD],
  uploadStats: getIgvUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: addIgv,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

import { connect } from 'react-redux'

import UploadFormPage from 'shared/components/page/UploadFormPage'
import { ANVIL_FIELDS } from 'shared/utils/constants'
import { updateIndividuals } from '../../reducers'
import { getGregorMetadataImportStats } from '../../selectors'

const mapStateToProps = state => ({
  fields: ANVIL_FIELDS,
  description: 'Import individuals and their metadata from the specified workspace',
  uploadStats: getGregorMetadataImportStats(state),
})

const mapDispatchToProps = {
  onSubmit: updateIndividuals,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import TextEditorModal from 'shared/components/modal/text-editor-modal/TextEditorModal'

import { updateIndividualsByGuid } from '../../../reducers/rootReducer'

export const EDIT_INDIVIDUAL_INFO_MODAL_ID = 'editIndividual'

const EditIndividualInfoModal = props =>
  <TextEditorModal modalId={EDIT_INDIVIDUAL_INFO_MODAL_ID} onSaveSuccess={props.onSaveSuccess} />

EditIndividualInfoModal.propTypes = {
  onSaveSuccess: PropTypes.func,
}

const mapDispatchToProps = {
  onSaveSuccess: updateIndividualsByGuid,
}

export default connect(null, mapDispatchToProps)(EditIndividualInfoModal)

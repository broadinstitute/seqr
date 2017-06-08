import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import TextEditorModal from 'shared/components/modal/text-editor-modal/TextEditorModal'

import { updateFamiliesByGuid } from '../../../reducers/rootReducer'

export const EDIT_FAMILY_INFO_MODAL_ID = 'editFamily'

const EditFamilyInfoModal = props =>
  <TextEditorModal modalId={EDIT_FAMILY_INFO_MODAL_ID} onSaveSuccess={props.onSaveSuccess} />

EditFamilyInfoModal.propTypes = {
  onSaveSuccess: PropTypes.func,
}

const mapDispatchToProps = {
  onSaveSuccess: updateFamiliesByGuid,
}

export default connect(null, mapDispatchToProps)(EditFamilyInfoModal)

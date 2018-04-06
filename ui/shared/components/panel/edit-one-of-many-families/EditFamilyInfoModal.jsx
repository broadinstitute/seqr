import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import RichTextEditorModal from 'shared/components/modal/text-editor-modal/RichTextEditorModal'
import { updateFamiliesByGuid } from 'redux/utils/commonDataActionsAndSelectors'

export const EDIT_FAMILY_INFO_MODAL_ID = 'editOneOfManyFamiliesInfoModal'

const EditFamilyInfoModal = props =>
  <RichTextEditorModal modalId={EDIT_FAMILY_INFO_MODAL_ID} onSaveSuccess={props.onSaveSuccess} />

EditFamilyInfoModal.propTypes = {
  onSaveSuccess: PropTypes.func,
}

const mapDispatchToProps = {
  onSaveSuccess: updateFamiliesByGuid,
}

export default connect(null, mapDispatchToProps)(EditFamilyInfoModal)

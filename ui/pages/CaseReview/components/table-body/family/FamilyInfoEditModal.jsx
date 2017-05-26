import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import RichTextEditorModal from 'shared/components/panel/rich-text-editor-modal/RichTextEditorModal'

import { updateFamiliesByGuid } from '../../../reducers/rootReducer'

export const FamilyInfoEditModalComponent = props =>
  <RichTextEditorModal onSaveSuccess={props.onSaveSuccess} />

FamilyInfoEditModalComponent.propTypes = {
  onSaveSuccess: PropTypes.func,
}

const mapDispatchToProps = {
  onSaveSuccess: updateFamiliesByGuid,
}

export default connect(null, mapDispatchToProps)(FamilyInfoEditModalComponent)

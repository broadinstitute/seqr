import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import RichTextEditorModal from 'shared/components/panel/rich-text-editor-modal/RichTextEditorModal'

import { updateIndividualsByGuid } from '../../../reducers/rootReducer'

export const IndividualInfoEditModalComponent = props =>
  <RichTextEditorModal onSaveSuccess={props.onSaveSuccess} />

IndividualInfoEditModalComponent.propTypes = {
  onSaveSuccess: PropTypes.func,
}

const mapDispatchToProps = {
  onSaveSuccess: updateIndividualsByGuid,
}

export default connect(null, mapDispatchToProps)(IndividualInfoEditModalComponent)

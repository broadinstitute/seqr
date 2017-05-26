/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Icon } from 'semantic-ui-react'

import StaffOnlyIcon from 'shared/components/icons/StaffOnlyIcon'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { showRichTextEditorModal } from 'shared/components/panel/rich-text-editor-modal/state'

const handleEditClick = props =>
  props.showRichTextEditorModal(props.richTextEditorModalTitle, props.initialText, props.richTextEditorModalSubmitUrl)

const RichTextFieldView = (props) => {
  if (!props.isEditable && !props.initialText) {
    return null
  }

  return <span>
    {props.isPrivate ? <StaffOnlyIcon /> : null}
    <b>{props.fieldName}: </b>
    <HorizontalSpacer width={20} />
    {props.isEditable ? <a tabIndex="0" onClick={() => handleEditClick(props)}><Icon link name="write" /></a> : null}
    <br />
    {props.initialText ?
      <div style={{ padding: '0px 0px 15px 22px', whiteSpace: 'normal' }} dangerouslySetInnerHTML={{ __html: props.initialText }} /> : null
    }
  </span>
}

export { RichTextFieldView as RichTextFieldViewComponent }

RichTextFieldView.propTypes = {
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  fieldName: PropTypes.string.isRequired,
  initialText: PropTypes.string,
  richTextEditorModalTitle: PropTypes.string,
  richTextEditorModalSubmitUrl: PropTypes.string,

  showRichTextEditorModal: PropTypes.func,
}

const mapDispatchToProps = dispatch => bindActionCreators({
  showRichTextEditorModal,
}, dispatch)

export default connect(null, mapDispatchToProps)(RichTextFieldView)

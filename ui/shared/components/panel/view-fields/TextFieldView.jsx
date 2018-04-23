/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'
import StaffOnlyIcon from 'shared/components/icons/StaffOnlyIcon'
import EditTextButton from 'shared/components/buttons/EditTextButton'
import { HorizontalSpacer } from 'shared/components/Spacers'

const TextFieldView = (props) => {
  if (props.isVisible !== undefined && !props.isVisible) {
    return null
  }
  if (!props.isEditable && !props.initialText) {
    return null
  }

  return (
    <span>
      {props.isPrivate && <StaffOnlyIcon />}
      {props.fieldName && (
        props.initialText ? <b>{props.fieldName}:</b> : <b>{props.fieldName}</b>
      )}
      <HorizontalSpacer width={20} />
      {props.isEditable &&
        <EditTextButton
          initialText={props.initialText}
          fieldId={props.fieldId}
          modalTitle={props.textEditorTitle}
          onSubmit={props.textEditorSubmit}
          modalId={props.textEditorId}
        />
      }
      <br />
      {
        props.initialText &&
        <div style={{ padding: '0px 0px 15px 22px' }}>
          <MarkdownRenderer markdown={props.initialText} options={{ breaks: true }} />
        </div>
      }
    </span>)
}

TextFieldView.propTypes = {
  isVisible: PropTypes.any,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  textEditorId: PropTypes.string,
  textEditorSubmit: PropTypes.func,
  textEditorTitle: PropTypes.string,
  fieldName: PropTypes.string.isRequired,
  fieldId: PropTypes.string,
  initialText: PropTypes.string,
}

export default TextFieldView

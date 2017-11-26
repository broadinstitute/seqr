/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'
import StaffOnlyIcon from 'shared/components/icons/StaffOnlyIcon'
import EditTextButton from 'shared/components/buttons/edit-text/EditTextButton'
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
          allowRichText={props.isRichText}
          initialText={props.initialText}
          modalTitle={props.textEditorTitle}
          modalSubmitUrl={props.textEditorSubmitUrl}
          modalId={props.textEditorId}
        />
      }
      <br />
      {
        props.initialText &&
        <div style={{ padding: '0px 0px 15px 22px', whiteSpace: 'normal' }}>
          <MarkdownRenderer markdown={props.initialText} />
        </div>
      }
    </span>)
}

TextFieldView.propTypes = {
  isVisible: PropTypes.any,
  isRichText: PropTypes.bool,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  textEditorId: PropTypes.string,
  textEditorSubmitUrl: PropTypes.string,
  textEditorTitle: PropTypes.string,
  fieldName: PropTypes.string.isRequired,
  initialText: PropTypes.string,
}

export default TextFieldView

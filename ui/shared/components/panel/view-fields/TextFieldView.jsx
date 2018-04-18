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
      {props.fieldName && <b>{props.fieldName}{props.initialText && ':'}<HorizontalSpacer width={20} /></b>}
      {props.isEditable &&
        <EditTextButton
          initialText={props.initialText}
          fieldId={props.fieldId}
          modalTitle={props.textEditorTitle}
          onSubmit={props.textEditorSubmit}
          modalId={props.textEditorId}
        />
      }
      {props.fieldName && <br />}
      {
        props.initialText &&
        <div style={{ padding: '0px 0px 15px 22px', display: props.fieldName ? 'block' : 'inline-block' }}>
          <MarkdownRenderer markdown={props.initialText} options={{ breaks: true }} style={props.textAnnotation ? { display: 'inline-block' } : {}} />
          {props.textAnnotation && <span><HorizontalSpacer width={20} />{props.textAnnotation}</span>}
        </div>
      }
    </span>)
}

TextFieldView.propTypes = {
  isVisible: PropTypes.any,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  isDeletable: PropTypes.bool,
  textEditorId: PropTypes.string,
  textEditorSubmit: PropTypes.func,
  textEditorTitle: PropTypes.string,
  fieldName: PropTypes.string,
  fieldId: PropTypes.string,
  initialText: PropTypes.string,
  textAnnotation: PropTypes.node,
}

export default TextFieldView

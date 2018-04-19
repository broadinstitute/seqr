import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'
import { Icon } from 'semantic-ui-react'

import StaffOnlyIcon from '../../icons/StaffOnlyIcon'
import EditTextButton from '../../buttons/EditTextButton'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import { HorizontalSpacer } from '../../Spacers'

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
      {props.isDeletable &&
        <DispatchRequestButton
          buttonContent={<Icon link name="trash" />}
          onSubmit={props.deleteSubmit}
          confirmDialog={`Are you sure you want to delete this ${props.fieldName || props.fieldId}?`}
        />
      }
      {props.fieldName && <br />}
      {
        props.initialText &&
        <div style={{ paddingBottom: '15px', paddingLeft: props.isDeletable ? 0 : ' 22px', display: props.fieldName ? 'block' : 'inline-block' }}>
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
  deleteSubmit: PropTypes.func,
  fieldName: PropTypes.string,
  fieldId: PropTypes.string,
  initialText: PropTypes.string,
  textAnnotation: PropTypes.node,
}

export default TextFieldView

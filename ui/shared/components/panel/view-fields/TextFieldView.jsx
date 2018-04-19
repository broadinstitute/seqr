import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'
import { Icon, Popup } from 'semantic-ui-react'

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
  const markdown = <MarkdownRenderer
    markdown={props.initialText || ''}
    options={{ breaks: true }}
    style={props.textAnnotation ? { display: 'inline-block' } : {}}
  />
  return (
    <div style={props.style || {}}>
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
          onSubmit={() => props.textEditorSubmit({ delete: true })}
          confirmDialog={props.deleteConfirm}
        />
      }
      {props.fieldName && <br />}
      {
        props.initialText &&
        <div style={{ paddingBottom: props.compact ? 0 : '15px', paddingLeft: props.isDeletable ? 0 : ' 22px', display: props.fieldName ? 'block' : 'inline-block' }}>
          {props.textPopupContent ?
            <Popup
              position="top center"
              size="tiny"
              trigger={markdown}
              content={props.textPopupContent}
            /> : markdown
          }
          {props.textAnnotation && <span><HorizontalSpacer width={10} />{props.textAnnotation}</span>}
        </div>
      }
    </div>)
}

TextFieldView.propTypes = {
  isVisible: PropTypes.any,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  isDeletable: PropTypes.bool,
  textEditorId: PropTypes.string,
  textEditorSubmit: PropTypes.func,
  textEditorTitle: PropTypes.string,
  deleteConfirm: PropTypes.string,
  fieldName: PropTypes.string,
  fieldId: PropTypes.string,
  initialText: PropTypes.string,
  textAnnotation: PropTypes.node,
  textPopupContent: PropTypes.node,
  compact: PropTypes.bool,
  style: PropTypes.object,
}

export default TextFieldView

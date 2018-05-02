import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'
import { Popup } from 'semantic-ui-react'

import RichTextEditor from '../../form/RichTextEditor'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

const TextFieldView = (props) => {
  const {
    textEditorTitle, textEditorSubmit, textEditorId, textPopupContent, textAnnotation, additionalEditFields = [],
    ...baseProps
  } = props
  return <BaseFieldView
    fieldDisplay={(initialText) => {
      const markdown = <MarkdownRenderer
        markdown={initialText || ''}
        options={{ breaks: true }}
        style={props.textAnnotation ? { display: 'inline-block' } : {}}
      />
      return (
        <span>
          {textPopupContent ?
            <Popup
              position="top center"
              size="tiny"
              trigger={markdown}
              content={textPopupContent}
            /> : markdown
          }
          {textAnnotation && <span><HorizontalSpacer width={10} />{textAnnotation}</span>}
        </span>
      ) }
    }
    formFields={[{ name: props.fieldId, component: RichTextEditor }, ...additionalEditFields]}
    modalTitle={textEditorTitle}
    onSubmit={textEditorSubmit}
    modalId={textEditorId}
    {...baseProps}
  />
}

TextFieldView.propTypes = {
  textEditorId: PropTypes.string,
  textEditorSubmit: PropTypes.func,
  textEditorTitle: PropTypes.string,
  additionalEditFields: PropTypes.array,
  fieldId: PropTypes.string,
  textAnnotation: PropTypes.node,
  textPopupContent: PropTypes.node,
}

export default TextFieldView

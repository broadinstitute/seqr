import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'
import { Popup } from 'semantic-ui-react'

import RichTextEditor from '../../form/RichTextEditor'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

const TextFieldView = (props) => {
  const { textPopupContent, textAnnotation, additionalEditFields = [], ...baseProps } = props
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
    formFields={[{ name: props.field, component: RichTextEditor }, ...additionalEditFields]}
    {...baseProps}
  />
}

TextFieldView.propTypes = {
  additionalEditFields: PropTypes.array,
  field: PropTypes.string.isRequired,
  textAnnotation: PropTypes.node,
  textPopupContent: PropTypes.node,
}

export default TextFieldView

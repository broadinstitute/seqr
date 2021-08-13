import React from 'react'
import PropTypes from 'prop-types'
import ReactMarkdown from 'react-markdown'
import styled from 'styled-components'

import RichTextEditor from '../../form/RichTextEditor'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

const MarkdownContainer = styled.div`
  display: ${props => (props.inline ? 'inline-block' : 'block')}; 
  white-space: pre-wrap;
`

const TextFieldView = React.memo((props) => {
  const { textPopup, textAnnotation, fieldValidator, additionalEditFields = [], ...baseProps } = props
  const fields = [{ name: props.field, component: RichTextEditor, validate: fieldValidator }, ...additionalEditFields]
  return <BaseFieldView
    fieldDisplay={(initialText) => {
      const markdown =
        <MarkdownContainer inline={!!textAnnotation}>
          <ReactMarkdown linkTarget="_blank">{initialText || ''}</ReactMarkdown>
        </MarkdownContainer>
      return (
        <span>
          {textPopup ? textPopup(markdown) : markdown}
          {textAnnotation && <span><HorizontalSpacer width={10} />{textAnnotation}</span>}
        </span>
      ) }
    }
    formFields={fields}
    {...baseProps}
  />
})

TextFieldView.propTypes = {
  additionalEditFields: PropTypes.array,
  field: PropTypes.string.isRequired,
  textAnnotation: PropTypes.node,
  textPopup: PropTypes.func,
  fieldValidator: PropTypes.func,
}

export default TextFieldView

import React from 'react'
import PropTypes from 'prop-types'
import ReactMarkdown from 'react-markdown'
import styled from 'styled-components'

import RichTextEditor from '../../form/RichTextEditor'
import { validators } from '../../form/ReduxFormWrapper'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

const MarkdownContainer = styled.div`
  display: ${props => (props.inline ? 'inline-block' : 'block')}; 
  white-space: pre-wrap;
`

const RICH_TEXT_FIELD = { component: RichTextEditor }
const REQUIRED_RICH_TEXT_FIELD = { ...RICH_TEXT_FIELD, validate: validators.required }

const markdownDisplay = (textPopup, textAnnotation) => (initialText) => {
  const markdown = (
    <MarkdownContainer inline={!!textAnnotation}>
      <ReactMarkdown linkTarget="_blank">{initialText || ''}</ReactMarkdown>
    </MarkdownContainer>
  )
  return (
    <span>
      {textPopup ? textPopup(markdown) : markdown}
      {textAnnotation && <HorizontalSpacer width={10} />}
      {textAnnotation}
    </span>
  )
}

const TextFieldView = React.memo((props) => {
  const { textPopup, textAnnotation, required, ...baseProps } = props
  return (
    <BaseFieldView
      fieldDisplay={markdownDisplay(textPopup, textAnnotation)}
      formFieldProps={required ? REQUIRED_RICH_TEXT_FIELD : RICH_TEXT_FIELD}
      {...baseProps}
    />
  )
})

TextFieldView.propTypes = {
  additionalEditFields: PropTypes.arrayOf(PropTypes.object),
  field: PropTypes.string.isRequired,
  textAnnotation: PropTypes.node,
  textPopup: PropTypes.func,
  required: PropTypes.bool,
}

export default TextFieldView

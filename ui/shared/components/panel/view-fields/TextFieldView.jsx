import React from 'react'
import PropTypes from 'prop-types'
import { Loader } from 'semantic-ui-react'
import styled from 'styled-components'

import { validators } from '../../form/FormHelpers'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

// Lazily loading components allows us to leave these libraries out of our bundle and only load them when needed
const ReactMarkdown = React.lazy(() => import('react-markdown'))
const RichTextEditor = React.lazy(() => import('../../form/RichTextEditor'))

const MarkdownContainer = styled.div`
  display: ${props => (props.inline ? 'inline-block' : 'block')};
  
  h4 + ul {
    list-style-type: none;
    
    ul {
      list-style-type: none;
    }
  }  
`

const MAPPED_HTML_COMPONENTS = { code: 'div', pre: 'p' }

const LazyRichTextEditor = props => <React.Suspense fallback={<Loader />}><RichTextEditor {...props} /></React.Suspense>

const RICH_TEXT_FIELD = { component: LazyRichTextEditor }
const REQUIRED_RICH_TEXT_FIELD = { ...RICH_TEXT_FIELD, validate: validators.required }

const markdownDisplay = (textPopup, textAnnotation) => (initialText) => {
  const markdown = (
    <MarkdownContainer inline={!!textAnnotation}>
      <React.Suspense fallback={<Loader />}>
        <ReactMarkdown linkTarget="_blank" components={MAPPED_HTML_COMPONENTS}>{initialText || ''}</ReactMarkdown>
      </React.Suspense>
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

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Viewer } from '@toast-ui/react-editor'

import RichTextEditor from '../../form/RichTextEditor'
import { validators } from '../../form/ReduxFormWrapper'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

const MarkdownContainer = styled.div`
  .tui-editor-contents {
    font-family: inherit;
    font-size: inherit;
  }
  display: ${props => (props.inline ? 'inline-block' : 'block')}; 
`

const RICH_TEXT_FIELD = { component: RichTextEditor }
const REQUIRED_RICH_TEXT_FIELD = { ...RICH_TEXT_FIELD, validate: validators.required }

const LINK_ATTRIBUTES = { target: '_blank' }

class MarkdownViewer extends React.PureComponent {

  propTypes = {
    value: PropTypes.string,
  }

  componentDidUpdate(prevProps) {
    const { value } = this.props
    if (value !== prevProps.value) {
      this.editorRef.getInstance().setMarkdown(value)
    }
  }

  setEditorRef = (element) => {
    this.editorRef = element
  }

  render() {
    const { value } = this.props
    return (
      <MarkdownContainer>
        <Viewer
          initialValue={value || ''}
          linkAttributes={LINK_ATTRIBUTES}
          ref={this.setEditorRef}
        />
      </MarkdownContainer>
    )
  }

}

const markdownDisplay = (textPopup, textAnnotation) => (initialText) => {
  const markdown = <MarkdownViewer value={initialText || ''} />
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

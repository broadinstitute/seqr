import React from 'react'
import PropTypes from 'prop-types'
import MarkdownRenderer from 'react-markdown-renderer'

import RichTextEditor from '../../form/RichTextEditor'
import { HorizontalSpacer } from '../../Spacers'
import BaseFieldView from './BaseFieldView'

const MARKDOWN_OPTIONS = { breaks: true }
const INLINE_STYLE = { display: 'inline-block' }

const TextFieldView = (props) => {
  const { textPopup, textAnnotation, additionalEditFields = [], ...baseProps } = props
  const fields = [{ name: props.field, component: RichTextEditor }, ...additionalEditFields]
  return <BaseFieldView
    fieldDisplay={(initialText) => {
      const style = props.textAnnotation ? INLINE_STYLE : {}
      const markdown = <MarkdownRenderer
        markdown={initialText || ''}
        options={MARKDOWN_OPTIONS}
        style={style}
      />
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
}

TextFieldView.propTypes = {
  additionalEditFields: PropTypes.array,
  field: PropTypes.string.isRequired,
  textAnnotation: PropTypes.node,
  textPopup: PropTypes.func,
}

export default TextFieldView

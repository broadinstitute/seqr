import React from 'react'
import styled from 'styled-components'
import PropTypes from 'prop-types'
import { Button, Segment } from 'semantic-ui-react'
import { Editor, EditorState, RichUtils, convertToRaw, convertFromRaw } from 'draft-js'
import { draftToMarkdown, markdownToDraft } from 'markdown-draft-js'

import 'draft-js/dist/Draft.css'

const ButtonContainer = styled(Segment)`
  padding: 0 !important;
`

const EditorContainer = styled(Segment)`
  min-width: 590px;
`

const INLINE_STYLES = [
  { label: 'Bold', type: 'BOLD', icon: 'bold' },
  { label: 'Italic', type: 'ITALIC', icon: 'italic' },
]

const BLOCK_TYPES = [
  { label: 'Bullet List', type: 'unordered-list-item', icon: 'unordered list' },
  { label: 'Numbered List', type: 'ordered-list-item', icon: 'ordered list' },
]

/*
 Draft.js-based rich text editor.
 It uses draftjs-md-converter to convert Draft.js content representation to/from Markdown.

 Style menu bar is based on this example:
 https://github.com/facebook/draft-js/blob/master/examples/draft-0-10-0/rich/rich.html
 */
class RichTextEditor extends React.PureComponent {

  static propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func,
  }

  static defaultProps = {
    onChange: () => {},
  }

  constructor(props) {
    super(props)

    const { value } = this.props
    let editorState
    if (value) {
      const rawData = markdownToDraft(value, { preserveNewlines: true })
      const contentState = convertFromRaw(rawData)
      editorState = EditorState.createWithContent(contentState)
    } else {
      editorState = EditorState.createEmpty()
    }

    this.state = { editorState } // eslint-disable-line react/state-in-constructor
  }

  componentDidMount() {
    this.editor.focus()
  }

  setEditorRef = (ref) => { this.editor = ref }

  getMarkdown() {
    const { editorState } = this.state
    const content = editorState.getCurrentContent()
    return draftToMarkdown(convertToRaw(content), { preserveNewlines: true })
  }

  updateEditorState = (editorState) => {
    const { onChange } = this.props
    this.setState({ editorState }, () => onChange(this.getMarkdown()))
  }

  handleKeyCommand = (command, editorState) => {
    const newState = RichUtils.handleKeyCommand(editorState, command)
    if (newState) {
      this.setState({ editorState: newState })
      return true
    }
    return false
  }

  toggleInlineStyle = (e, data) => {
    const { editorState } = this.state
    e.preventDefault()
    this.updateEditorState(RichUtils.toggleInlineStyle(editorState, data.id))
  }

  toggleBlockStyle = (e, data) => {
    const { editorState } = this.state
    e.preventDefault()
    this.updateEditorState(RichUtils.toggleBlockType(editorState, data.id))
  }

  render() {
    const { editorState: es } = this.state
    const currentInlineStyle = es.getCurrentInlineStyle()
    const currentBlockType = es.getCurrentContent().getBlockForKey(es.getSelection().getStartKey()).getType()
    return (
      <div>
        <ButtonContainer basic textAlign="right">
          {INLINE_STYLES.map(type => (
            <Button
              id={type.type}
              key={type.label}
              size="tiny"
              icon={type.icon}
              active={currentInlineStyle.has(type.type)}
              onClick={this.toggleInlineStyle}
              toggle
            />
          ))}
          &nbsp; &nbsp;
          {BLOCK_TYPES.map(type => (
            <Button
              id={type.type}
              key={type.label}
              size="tiny"
              icon={type.icon}
              active={type.type === currentBlockType}
              onClick={this.toggleBlockStyle}
              toggle
            />
          ))}
        </ButtonContainer>
        <EditorContainer>
          <Editor
            editorState={es}
            handleKeyCommand={this.handleKeyCommand}
            placeholder=""
            ref={this.setEditorRef}
            onChange={this.updateEditorState}
          />
        </EditorContainer>
      </div>
    )
  }

}

export default RichTextEditor

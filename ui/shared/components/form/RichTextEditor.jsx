/* eslint-disable no-underscore-dangle */

import React from 'react'
import PropTypes from 'prop-types'
import { Button } from 'semantic-ui-react'
import { Editor, EditorState, RichUtils, convertToRaw, convertFromRaw } from 'draft-js'
import { mdToDraftjs, draftjsToMd } from 'draftjs-md-converter'

import 'draft-js/dist/Draft.css'

/*
 Draft.js-based rich text editor.
 It uses draftjs-md-converter to convert Draft.js content representation to/from Markdown.

 Style menu bar is based on this example:
 https://github.com/facebook/draft-js/blob/master/examples/draft-0-10-0/rich/rich.html
 */
class RichTextEditor extends React.Component {
  static propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func,
  }

  static BLOCK_TYPES = [
    { label: 'Bullet List', type: 'unordered-list-item', icon: 'unordered list' },
    { label: 'Numbered List', type: 'ordered-list-item', icon: 'ordered list' },
  ]

  static INLINE_STYLES = [
    { label: 'Bold', type: 'BOLD', icon: 'bold' },
    { label: 'Italic', type: 'ITALIC', icon: 'italic' },
    { label: 'Underline', type: 'UNDERLINE', icon: 'underline' },
  ]

  static defaultProps = {
    onChange: () => {},
  }

  constructor(props) {
    super(props)

    let editorState
    if (this.props.value) {
      const rawData = mdToDraftjs(this.props.value || '')
      const contentState = convertFromRaw(rawData)
      editorState = EditorState.createWithContent(contentState)
    } else {
      editorState = EditorState.createEmpty()
    }

    this.state = { editorState }

    this.handleKeyCommand = this._handleKeyCommand.bind(this)
    this.setEditorRef = (ref) => { this.editor = ref }
  }

  getMarkdown() {
    const content = this.state.editorState.getCurrentContent()
    return draftjsToMd(convertToRaw(content))
  }

  _handleKeyCommand(command, editorState) {
    const newState = RichUtils.handleKeyCommand(editorState, command)
    if (newState) {
      this.setState({ editorState: newState })
      return true
    }
    return false
  }

  updateEditorState = (editorState) => {
    this.setState({ editorState }, () => this.props.onChange(this.getMarkdown()))
  }

  render() {
    const es = this.state.editorState
    return (
      <div>
        <div style={{ padding: '0px 0px 10px 0px', textAlign: 'right' }}>
          <InlineStyleButtonPanel
            currentInlineStyle={es.getCurrentInlineStyle()}
            onButtonClick={(e, data) => {
              e.preventDefault()
              this.updateEditorState(RichUtils.toggleInlineStyle(es, data.id))
            }}
          />
          {' '}
          <BlockTypeButtonPanel
            currentBlockType={es.getCurrentContent().getBlockForKey(es.getSelection().getStartKey()).getType()}
            onButtonClick={(e, data) => {
              e.preventDefault()
              this.updateEditorState(RichUtils.toggleBlockType(es, data.id))
            }}
          />
        </div>
        <div style={{ border: '1px #DDD solid', padding: '10px' }}>
          <Editor
            editorState={this.state.editorState}
            handleKeyCommand={this.handleKeyCommand}
            placeholder=""
            ref={this.setEditorRef}
            onChange={this.updateEditorState}
          />
        </div>
      </div>)
  }

  componentDidMount() {
    this.editor.focus()
  }
}

const InlineStyleButtonPanel = props => (
  <div style={{ display: 'inline' }}>
    {
      RichTextEditor.INLINE_STYLES.map(type =>
        <Button
          id={type.type}
          key={type.label}
          size="tiny"
          icon={type.icon}
          active={props.currentInlineStyle.has(type.type)}
          onClick={props.onButtonClick}
          toggle
        />)
    }
  </div>)

InlineStyleButtonPanel.propTypes = {
  currentInlineStyle: PropTypes.object.isRequired,
  onButtonClick: PropTypes.func.isRequired,
}

const BlockTypeButtonPanel = props => (
  <div style={{ display: 'inline' }}>
    {
      RichTextEditor.BLOCK_TYPES.map(type =>
        <Button
          id={type.type}
          key={type.label}
          size="tiny"
          icon={type.icon}
          active={type.type === props.currentBlockType}
          onClick={props.onButtonClick}
          toggle
        />)
    }
  </div>
)

BlockTypeButtonPanel.propTypes = {
  currentBlockType: PropTypes.string.isRequired,
  onButtonClick: PropTypes.func.isRequired,
}

export default RichTextEditor

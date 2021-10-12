/* eslint-disable no-underscore-dangle */

import React from 'react'
import PropTypes from 'prop-types'
import { Button } from 'semantic-ui-react'
import { Editor, EditorState, RichUtils, convertToRaw, convertFromRaw } from 'draft-js'
import { draftToMarkdown, markdownToDraft } from 'markdown-draft-js'

import 'draft-js/dist/Draft.css'

const TAB = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'

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

  static BLOCK_TYPES = [
    { label: 'Bullet List', type: 'unordered-list-item', icon: 'unordered list' },
    { label: 'Numbered List', type: 'ordered-list-item', icon: 'ordered list' },
  ]

  static INLINE_STYLES = [
    { label: 'Bold', type: 'BOLD', icon: 'bold' },
    { label: 'Italic', type: 'ITALIC', icon: 'italic' },
  ]

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

    this.handleKeyCommand = this._handleKeyCommand.bind(this)
    this.setEditorRef = (ref) => { this.editor = ref }
  }

  componentDidMount() {
    this.editor.focus()
  }

  getMarkdown() {
    const { editorState } = this.state
    const content = editorState.getCurrentContent()
    const markdown = draftToMarkdown(convertToRaw(content), { preserveNewlines: true })
    // Support for tabs. Required for RGP datstat imported notes
    return markdown ? markdown.replace(/' '{5}/g, TAB).replace(/\u00A0{5}/g, TAB) : markdown
  }

  updateEditorState = (editorState) => {
    const { onChange } = this.props
    this.setState({ editorState }, () => onChange(this.getMarkdown()))
  }

  _handleKeyCommand(command, editorState) {
    const newState = RichUtils.handleKeyCommand(editorState, command)
    if (newState) {
      this.setState({ editorState: newState })
      return true
    }
    return false
  }

  render() {
    const { editorState: es } = this.state
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
        <div style={{ minWidth: '590px', border: '1px #DDD solid', padding: '10px' }}>
          <Editor
            editorState={es}
            handleKeyCommand={this.handleKeyCommand}
            placeholder=""
            ref={this.setEditorRef}
            onChange={this.updateEditorState}
          />
        </div>
      </div>
    )
  }

}

const InlineStyleButtonPanel = React.memo(props => (
  <div style={{ display: 'inline' }}>
    {RichTextEditor.INLINE_STYLES.map(type => (
      <Button
        id={type.type}
        key={type.label}
        size="tiny"
        icon={type.icon}
        active={props.currentInlineStyle.has(type.type)}
        onClick={props.onButtonClick}
        toggle
      />
    ))}
  </div>
))

InlineStyleButtonPanel.propTypes = {
  currentInlineStyle: PropTypes.object.isRequired,
  onButtonClick: PropTypes.func.isRequired,
}

const BlockTypeButtonPanel = React.memo(props => (
  <div style={{ display: 'inline' }}>
    {RichTextEditor.BLOCK_TYPES.map(type => (
      <Button
        id={type.type}
        key={type.label}
        size="tiny"
        icon={type.icon}
        active={type.type === props.currentBlockType}
        onClick={props.onButtonClick}
        toggle
      />
    ))}
  </div>
))

BlockTypeButtonPanel.propTypes = {
  currentBlockType: PropTypes.string.isRequired,
  onButtonClick: PropTypes.func.isRequired,
}

export default RichTextEditor

import React from 'react'
import styled from 'styled-components'
import PropTypes from 'prop-types'
import { Editor } from '@toast-ui/react-editor'

import '@toast-ui/editor/dist/toastui-editor.css'

const EditorContainer = styled.div`
  .tui-editor-contents {
    font-family: 'Lato';
    font-size: inherit;
  }
  
  .tui-editor-defaultUI-toolbar {
    background-color: #e0e1e2;
     
    button {
      background-color: #e0e1e2;
      border: none;
        
      &:hover, &.active {
        background-color: #cacbcd;
      }
    }
    
    .tui-toolbar-divider {
      background-color: ##999999;
    }
  }
`

const TOOLBAR = ['bold', 'italic', 'divider', 'ul', 'ol']

class RichTextEditor extends React.PureComponent {

  propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func,
  }

  handleChange = () => {
    const { onChange } = this.props
    onChange(this.editorRef.getInstance().getMarkdown())
  }

  setEditorRef = (element) => {
    this.editorRef = element
  }

  render() {
    const { value } = this.props
    return (
      <EditorContainer>
        <Editor
          initialValue={value}
          onChange={this.handleChange}
          initialEditType="wysiwyg"
          hideModeSwitch
          usageStatistics={false}
          toolbarItems={TOOLBAR}
          ref={this.setEditorRef}
        />
      </EditorContainer>
    )
  }

}

export default RichTextEditor

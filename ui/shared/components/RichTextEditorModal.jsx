import React from 'react'
import { Button, Confirm, Form } from 'semantic-ui-react'

import { HttpPost } from '../utils/httpPostHelper'
import Modal from './Modal'
import { HorizontalSpacer } from './Spacers'
import RichTextEditor from './RichTextEditor'
import SaveStatus from './form/SaveStatus'


class RichTextEditorModal extends React.Component
{
  static propTypes = {
    title: React.PropTypes.string.isRequired,
    formSubmitUrl: React.PropTypes.string.isRequired,
    onSave: React.PropTypes.func,
    onClose: React.PropTypes.func.isRequired,
    initialText: React.PropTypes.string,
  }

  constructor(props) {
    super(props)

    this.state = {
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
      confirmClose: false,
    }

    this.savedText = null

    this.httpPostSubmitter = new HttpPost(
      this.props.formSubmitUrl,
      (responseJson) => {
        if (this.props.onSave) {
          this.props.onSave(responseJson)
        }
        this.handleClose()
      },
      (exception) => {
        this.savedText = '--trigger "unsaved text" warning on close--'
        this.setState({ saveStatus: SaveStatus.ERROR, saveErrorMessage: exception.message.toString() })
      },
    )
  }

  getTextEditorContent = () => {
    if (window && window.tinyMCE) {
      const editor = window.tinyMCE.get('RichTextEditor')
      let content = editor.getContent()
      if (content === '<div>&nbsp;</div>') {
        content = ''
      }
      return content
    }
    return undefined
  }

  componentDidMount() {
    if (this.savedText === null) {
      /*
      the TinyMCE component sometimes alters its initial text slightly relative to
      this.props.initialText, so setting this.savedText = this.props.initialText in the constructor
      still sometimes causes the "Unsaved text. Are you sure you want to close?" message to show,
      even when the user didn't make any changes. This getTextEditorContent() call works around that.
      */
      this.savedText = this.getTextEditorContent()
    }
  }

  handleSave = (e) => {
    e.preventDefault()

    this.savedText = this.getTextEditorContent()

    this.setState({ saveStatus: SaveStatus.IN_PROGRESS, saveErrorMessage: null })
    this.httpPostSubmitter.submit({ form: this.savedText })
  }

  handleClose = (allowCancel) => {
    if (allowCancel && this.getTextEditorContent() !== this.savedText) {
      this.setState({ confirmClose: true })
    } else {
      this.props.onClose()
    }
  }

  render() {
    return <Modal title={this.props.title} onClose={() => this.handleClose(true)}>
      <Form onSubmit={this.handleSave}>

        <RichTextEditor id="RichTextEditor" initialText={this.props.initialText} />

        <div style={{ margin: '15px 0px 15px 10px', width: '100%', align: 'center' }}>
          <Button
            onClick={(e) => { e.preventDefault(); this.handleClose(true) }}
            style={{ padding: '5px', width: '100px' }}
          >
            Cancel
          </Button>
          <HorizontalSpacer width={10} />
          <Button
            color="vk"
            type="submit"
            style={{ padding: '5px', width: '100px' }}
          >
            Submit
          </Button>
          <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
        </div>

        <Confirm
          content="Editor contains unsaved changes. Are you sure you want to close it?"
          open={this.state.confirmClose}
          onCancel={() => this.setState({ confirmClose: false })}
          onConfirm={() => this.handleClose(false)}
        />
      </Form>
    </Modal>
  }
}


export default RichTextEditorModal

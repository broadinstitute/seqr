/* eslint-disable */

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Button, Confirm, Form } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { HorizontalSpacer } from 'shared/components/Spacers'
import RichTextEditor from 'shared/components/form/RichTextEditor'
import SaveStatus from 'shared/components/form/SaveStatus'
import Modal from 'shared/components/modal/Modal'

import {
  getRichTextEditorModalIsVisible,
  getRichTextEditorModalTitle,
  getRichTextEditorModalInitialText,
  getRichTextEditorModalSubmitUrl,
  hideRichTextEditorModal,
} from './state'

class RichTextEditorModal extends React.Component
{
  static propTypes = {
    isVisible: PropTypes.bool.isRequired,
    title: PropTypes.string,
    initialText: PropTypes.string,
    formSubmitUrl: PropTypes.string,
    onSave: PropTypes.func,
    onClose: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = {
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
      confirmClose: false,
    }

    this.savedText = null

    this.httpRequestHelper = new HttpRequestHelper(
      this.props.formSubmitUrl,
      (responseJson) => {
        if (this.props.onSave) {
          this.props.onSave(responseJson)
        }
        this.handleClose()
      },
      (exception) => {
        console.log(exception)
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
    if (this.props.isVisible && this.savedText === null) {
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
    this.httpRequestHelper.post({ form: this.savedText })
  }

  handleClose = (allowCancel) => {
    if (allowCancel && this.getTextEditorContent() !== this.savedText) {
      this.setState({ confirmClose: true })
    } else {
      this.props.onClose()
    }
  }

  render() {
    if (!this.props.isVisible) {
      return null
    }

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

export { RichTextEditorModal as RichTextEditorModalComponent }

const mapStateToProps = state => ({
  isVisible: getRichTextEditorModalIsVisible(state),
  title: getRichTextEditorModalTitle(state),
  initialText: getRichTextEditorModalInitialText(state),
  formSubmitUrl: getRichTextEditorModalSubmitUrl(state),
})


const createRichTextEditorModal = (onSave, onClose) => {


  const mapDispatchToProps = dispatch => bindActionCreators({
    onSave: () => {
      console.log('onSave called')
    },
    onClose: () => {
      console.log('onClose called')
      if (onClose !== null) {
        onClose()
      }
      return hideRichTextEditorModal()
    },
  }, dispatch)

  return connect(mapStateToProps, mapDispatchToProps)(RichTextEditorModal)
}


export default createRichTextEditorModal


//export default connect(mapStateToProps)(RichTextEditorModal)
/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Button, Confirm, Form } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { HorizontalSpacer } from 'shared/components/Spacers'
import RichTextEditor from 'shared/components/form/RichTextEditor'
import SaveStatus from 'shared/components/form/SaveStatus'
import Modal from 'shared/components/modal/Modal'

import {
  DEFAULT_TEXT_EDITOR_MODAL_ID,
  getTextEditorModals,
  initTextEditorModal,
  hideTextEditorModal,
} from './state'

class TextEditorModal extends React.Component
{
  static propTypes = {
    /* the id, if specified, can be used to create more than one dialog */
    modalId: PropTypes.string,
    textEditorModals: PropTypes.object.isRequired,
    onSaveSuccess: PropTypes.func,
    initTextEditorModal: PropTypes.func.isRequired,
    hideTextEditorModal: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)
    props.initTextEditorModal(props.modalId || DEFAULT_TEXT_EDITOR_MODAL_ID)
    this.resetState()
  }

  componentWillReceiveProps(nextProps) {
    if (this.props !== nextProps) {
      this.initHttpRequestHelper(nextProps)
    }
  }

  resetState = () => {
    this.state = {
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
      confirmClose: false,
    }

    this.savedText = null
  }

  initHttpRequestHelper = (props) => {
    const modalState = props.textEditorModals[props.modalId || DEFAULT_TEXT_EDITOR_MODAL_ID]
    this.httpRequestHelper = new HttpRequestHelper(
      modalState.formSubmitUrl,
      (responseJson) => {
        if (props.onSaveSuccess) {
          props.onSaveSuccess(responseJson)
        }
        this.performClose(false)
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

  componentDidUpdate() {
    const modalState = this.props.textEditorModals[this.props.modalId || DEFAULT_TEXT_EDITOR_MODAL_ID]
    const isVisible = modalState.isVisible
    if (isVisible && this.savedText === null) {
      /*
      the TinyMCE component sometimes alters its initial text slightly relative to
      this.props.initialText, so setting this.savedText = this.props.initialText in the constructor
      still sometimes causes the "Unsaved text. Are you sure you want to close?" message to show,
      even when the user didn't make any changes. This getTextEditorContent() call works around that.
      */
      this.savedText = this.getTextEditorContent()
    }
  }

  performSave = (e) => {
    e.preventDefault()

    this.savedText = this.getTextEditorContent()

    this.setState({ saveStatus: SaveStatus.IN_PROGRESS, saveErrorMessage: null })
    this.httpRequestHelper.post({ value: this.savedText })
  }

  performClose = (allowCancel) => {
    if (allowCancel && this.getTextEditorContent() !== this.savedText) {
      this.setState({ confirmClose: true })
    } else {
      this.resetState()
      this.props.hideTextEditorModal(this.props.modalId)
    }
  }

  render() {
    const modalState = this.props.textEditorModals[this.props.modalId || DEFAULT_TEXT_EDITOR_MODAL_ID]
    if (!modalState || !modalState.isVisible) {
      return null
    }
    const initialText = modalState.initialText || ''
    return <Modal title={modalState.title} onClose={() => this.performClose(true)}>
      <Form onSubmit={this.performSave}>

        <RichTextEditor id="RichTextEditor" initialText={initialText} />

        <div style={{ margin: '15px 0px 15px 10px', width: '100%', align: 'center' }}>
          <Button
            onClick={(e) => { e.preventDefault(); this.performClose(true) }}
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
          onConfirm={() => this.performClose(false)}
        />
      </Form>
    </Modal>
  }
}

export { TextEditorModal as TextEditorModalComponent }

const mapStateToProps = state => ({
  textEditorModals: getTextEditorModals(state),
})

const mapDispatchToProps = {
  initTextEditorModal,
  hideTextEditorModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(TextEditorModal)

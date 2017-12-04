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
  getRichTextEditorModals,
  initRichTextEditorModal,
  hideRichTextEditorModal,
} from './state'

class RichTextEditorModal extends React.Component
{
  static propTypes = {
    /* the id, if specified, can be used to create more than one dialog */
    modalId: PropTypes.string.isRequired,
    modalSettings: PropTypes.object,
    onSaveSuccess: PropTypes.func,
    initModal: PropTypes.func.isRequired,
    hideModal: PropTypes.func.isRequired,
  }

  static DEFAULT_STATE = {
    saveStatus: SaveStatus.NONE,
    saveErrorMessage: null,
    confirmClose: false,
  }

  constructor(props) {
    super(props)
    props.initModal(props.modalId)

    this.state = RichTextEditorModal.DEFAULT_STATE
    this.resetTextVars(props)
  }

  resetTextVars(props) {
    this.savedText = props.modalSettings ? props.modalSettings.initialText : ''
    this.currentText = this.savedText
  }

  componentWillReceiveProps(nextProps) {
    if (this.props !== nextProps) {
      this.resetTextVars(nextProps)
      this.initHttpRequestHelper(nextProps)
    }
  }


  initHttpRequestHelper = (props) => {
    this.httpRequestHelper = new HttpRequestHelper(
      props.modalSettings.formSubmitUrl,
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

  performSave = (e) => {
    e.preventDefault()
    this.savedText = this.currentText
    this.setState({ saveStatus: SaveStatus.IN_PROGRESS, saveErrorMessage: null })
    this.httpRequestHelper.post({ value: this.currentText })
  }

  performClose = (possibleToCancel) => {
    if (this.currentText !== this.savedText && possibleToCancel) {
      this.setState({ confirmClose: true })
    } else {
      this.setState(RichTextEditorModal.DEFAULT_STATE)
      this.props.hideModal(this.props.modalId)
    }
  }

  render() {
    if (!this.props.modalSettings) {
      return null
    }
    const { isVisible, initialText, title } = this.props.modalSettings

    if (!isVisible) {
      return null
    }

    return (
      <Modal title={title} handleClose={() => this.performClose(true)}>
        <Form onSubmit={this.performSave}>

          <RichTextEditor initialText={initialText || ''} onChange={(currentText) => { this.currentText = currentText }} />

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
      </Modal>)
  }
}

export { RichTextEditorModal as RichTextEditorModalComponent }

const mapStateToProps = (state, ownProps) => {
  const richTextEditorModals = getRichTextEditorModals(state)
  return {
    modalSettings: richTextEditorModals && richTextEditorModals[ownProps.modalId],
  }
}

const mapDispatchToProps = {
  initModal: initRichTextEditorModal,
  hideModal: hideRichTextEditorModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(RichTextEditorModal)

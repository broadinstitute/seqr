/* eslint no-underscore-dangle: 0 */

import React from 'react'
import { Button, Confirm, Form, Message } from 'semantic-ui-react'
import isEqual from 'lodash/isEqual'

import { HttpRequestHelper } from '../utils/httpRequestHelper'
import Modal from './Modal'
import { HorizontalSpacer } from './Spacers'
import SaveStatus from './form/SaveStatus'

/**
 * Modal dialog that contains form elements.
 */
class ModalWithForm extends React.Component
{
  static propTypes = {
    title: React.PropTypes.string.isRequired,
    formSubmitUrl: React.PropTypes.string.isRequired,
    onValidate: React.PropTypes.func,
    onSave: React.PropTypes.func,
    onClose: React.PropTypes.func,
    confirmCloseIfNotSaved: React.PropTypes.bool.isRequired,
    children: React.PropTypes.element.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = {
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
      confirmClose: false,
      formFieldsWithError: {},
    }

    this.formSerializer = null
    this.formComponentRef = null
    this.originalFormData = {}

    this.httpRequestHelper = new HttpRequestHelper(
      this.props.formSubmitUrl,
      (responseJson) => {
        if (this.props.onSave) {
          this.props.onSave(responseJson)
        }
        this.handleClose()
      },
      (exception) => {
        this.setState({
          saveStatus: SaveStatus.ERROR,
          saveErrorMessage: exception.message.toString(),
        })
      },
    )
  }

  componentDidMount = () => {
    this.originalFormData = this.getFormData()
  }

  getFormData = () => {
    if (this.formSerializer === null) {
      return null
    }

    const serializedFormData = this.formSerializer(this.formComponentRef)

    return serializedFormData
  }

  formHasBeenModified = () => {
    return !isEqual(this.originalFormData, this.getFormData())
  }

  handleSave = (e) => {
    e.preventDefault()

    const formData = this.getFormData()
    if (this.props.onValidate) {
      const formFieldsWithError = this.props.onValidate(formData)
      this.setState({ formFieldsWithError })
      if (formFieldsWithError && Object.keys(formFieldsWithError).length > 0) {
        return  // don't submit the form
      }
    }

    this.setState({ saveStatus: SaveStatus.IN_PROGRESS, saveErrorMessage: null })
    this.httpRequestHelper.post({ form: formData })
  }

  handleClose = (confirmCloseIfNecessary) => {
    if (confirmCloseIfNecessary && this.props.confirmCloseIfNotSaved && this.formHasBeenModified()) {
      //first double check that user wants to close
      this.setState({ confirmClose: true })
    } else if (this.props.onClose) {
      this.props.onClose()
    }
  }

  render() {
    const children = React.Children.map(
      this.props.children,
      (child) => {
        const showError = child.props.name && this.state.formFieldsWithError[child.props.name] !== undefined
        return React.cloneElement(child, { error: showError })
      },
    )

    const formComponent = <Form ref={this.handleFormRef} onSubmit={this.handleSave}>
      {children}
    </Form>

    this.formSerializer = formComponent.props.serializer // save the serializer for use in getFormData()

    const buttonPanel = <div style={{ margin: '15px 0px 15px 10px', width: '100%', textAlign: 'right' }}>
      <Button
        onClick={(e) => { e.preventDefault(); this.handleClose(true) }}
        style={{ padding: '5px', width: '100px' }}
      >
        Cancel
      </Button>
      <HorizontalSpacer width={10} />
      <Button
        onClick={this.handleSave}
        type="submit"
        color="vk"
        style={{ padding: '5px', width: '100px' }}
      >
        Submit
      </Button>
      <HorizontalSpacer width={5} />
      <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
      <HorizontalSpacer width={5} />
    </div>

    const errorMessageBox = Object.keys(this.state.formFieldsWithError).length > 0 ?
      <Message error style={{ textAlign: 'left' }} header="Error" list={
        Object.entries(this.state.formFieldsWithError).map(([key, value]) => {
          return `${key} ${value}`
        })}
      /> : null

    const confirmCloseDialog = <Confirm
      content="Editor contains unsaved changes. Are you sure you want to close it?"
      open={this.state.confirmClose}
      onCancel={() => this.setState({ confirmClose: false })}
      onConfirm={() => this.handleClose(false)}
    />

    return <Modal title={this.props.title} onClose={() => this.handleClose(true)}>
      <div>
        {formComponent}
        {errorMessageBox}
        {buttonPanel}
        {confirmCloseDialog}
      </div>
    </Modal>
  }

  handleFormRef = (ref) => {
    if (ref) {
      this.formComponentRef = ref._form
    }
  }
}


export default ModalWithForm

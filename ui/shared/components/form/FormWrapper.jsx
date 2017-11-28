/* eslint-disable no-underscore-dangle */
/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'

import { Button, Confirm, Form, Message } from 'semantic-ui-react'
import isEqual from 'lodash/isEqual'

import { HttpRequestHelper } from '../../utils/httpRequestHelper'
import { HorizontalSpacer } from '../Spacers'
import SaveStatus from '../form/SaveStatus'


/**
 * Form wrapper that provides Submit and Cancel functionality.
 */
class FormWrapper extends React.Component
{
  static propTypes = {
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,
    formSubmitUrl: PropTypes.string,
    onValidate: PropTypes.func,
    onSave: PropTypes.func,
    onClose: PropTypes.func,
    confirmCloseIfNotSaved: PropTypes.bool.isRequired,
    children: PropTypes.node,
    getFormDataJson: PropTypes.func, // required if either onValidate or formSubmitUrl is provided
  }

  constructor(props) {
    super(props)

    this.state = {
      saveStatus: SaveStatus.NONE, // one of NONE, IN_PROGRESS, SUCCEEDED, ERROR
      saveErrorMessage: null,
      confirmClose: false, // whether to ask the user when closing the form without saving
      errors: {},
      warnings: {},
      info: {},
    }
  }

  componentWillReceiveProps() {
    if (this.props.onValidate) {
      const formData = this.props.getFormDataJson()
      const validationResult = this.props.onValidate(formData)
      this.setState(validationResult)
    }
  }

  hasFormBeenModified = () => {
    return !isEqual(this.originalFormData, this.props.getFormDataJson())
  }

  doSave = (e) => {
    e.preventDefault()

    let validationResult = null
    if (this.props.onValidate) {
      validationResult = this.props.onValidate(this.props.getFormDataJson())
      this.setState(validationResult)

      if (validationResult && validationResult.errors && Object.keys(validationResult.errors).length > 0) {
        return // don't submit the form if there are errors
      }
    }

    this.setState({ saveStatus: SaveStatus.IN_PROGRESS, saveErrorMessage: null })

    const formSubmitUrl = (validationResult && validationResult.formSubmitUrl) || this.props.formSubmitUrl
    if (formSubmitUrl) {
      const httpRequestHelper = new HttpRequestHelper(
        formSubmitUrl,
        (responseJson) => {
          if (this.props.onSave) {
            this.props.onSave(responseJson)
          }
          this.doClose(false)
        },
        (exception) => {
          console.log(exception)
          this.setState({
            saveStatus: SaveStatus.ERROR,
            saveErrorMessage: exception.message.toString(),
          })
        },
      )

      httpRequestHelper.post({ form: this.props.getFormDataJson() })
    } else {
      this.doClose(false)
    }
  }

  doClose = (confirmCloseIfNecessary) => {
    if (confirmCloseIfNecessary && this.props.confirmCloseIfNotSaved && this.hasFormBeenModified()) {
      //first double check that user wants to close
      this.setState({ confirmClose: true })
    } else if (this.props.onClose) {
      this.props.onClose()
    }
  }

  renderForm() {
    const children = React.Children.map(
      this.props.children,
      child => (
        child.props && child.props.name && this.state.errors && this.state.errors[child.props.name] !== undefined ?
          React.cloneElement(child, { error: true }) : child
      ),
    )

    return (
      <Form onSubmit={this.doSave} style={{ textAlign: 'left' }}>
        {children}
      </Form>
    )
  }

  renderMessageBoxes() {
    return (
      <span style={{ textAlign: 'left' }}>
        {
          (Object.keys(this.state.info).length > 0) &&
          <Message info style={{ marginTop: '10px' }}>
            {Object.values(this.state.info).map((info, i) => <div key={i}>{info}<br /></div>)}
          </Message>
        }
        {
          (Object.keys(this.state.warnings).length > 0) &&
          <Message warning style={{ marginTop: '10px' }}>
            {Object.values(this.state.warnings).map((warning, i) => <div key={i}><b>WARNING:</b> {warning}<br /></div>)}
          </Message>
        }
        {
          (Object.keys(this.state.errors).length > 0) &&
          <Message error style={{ marginTop: '10px' }}>
            {Object.values(this.state.errors).map((error, i) => <div key={i}><b>ERROR:</b> {error}<br /></div>)}
          </Message>
        }
      </span>)
  }

  renderButtonPanel() {
    return (
      <div style={{ margin: '15px 0px 15px 10px', width: '100%', textAlign: 'right' }}>
        <Button
          onClick={(e) => { e.preventDefault(); this.doClose(true) }}
          style={{ padding: '5px', width: '100px' }}
        >
          {this.props.cancelButtonText || 'Cancel'}
        </Button>
        <HorizontalSpacer width={10} />
        <Button
          onClick={this.doSave}
          type="submit"
          color="vk"
          style={{ padding: '5px', width: '100px' }}
        >
          {this.props.submitButtonText || 'Submit'}
        </Button>
        <HorizontalSpacer width={5} />
        <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
        <HorizontalSpacer width={5} />
      </div>)
  }

  renderConfirmCloseDialog() {
    return <Confirm
      content="Editor contains unsaved changes. Are you sure you want to close it?"
      open={this.state.confirmClose}
      onCancel={() => this.setState({ confirmClose: false })}
      onConfirm={() => this.doClose(false)}
    />
  }

  render() {
    return (
      <div>
        {this.renderForm()}
        {this.renderMessageBoxes()}
        {this.renderButtonPanel()}
        {this.renderConfirmCloseDialog()}
      </div>
    )
  }

}


export default FormWrapper

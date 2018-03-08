import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Confirm } from 'semantic-ui-react'

import RequestStatus from 'shared/components/form/RequestStatus'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'


const ButtonContainer = styled.div`
  display: inline-block;
  whitespace: nowrap;
`

class SendRequestButton extends React.Component {

  static propTypes = {

    /** React component to show */
    button: PropTypes.node.isRequired,

    /** URL where to send the request */
    requestUrl: PropTypes.string.isRequired,

    /** Whether to show a confirm dialog before submitting the request */
    showConfirmDialogBeforeSending: PropTypes.string,

    /** Returns the json object to send to the server */
    getDataToSend: PropTypes.func.isRequired,

    /** Function for handling the server response object upon successful request completion. */
    onRequestSuccess: PropTypes.func,

    /** Function for handling server communication error. */
    onRequestError: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.state = {
      requestStatus: RequestStatus.NONE,
      requestErrorMessage: null,
      isConfirmDialogVisible: false,
    }
  }

  render() {
    const Button = React.cloneElement(
      this.props.button,
      {
        onClick: (e) => {
          e.preventDefault()
          this.handleButtonClick({
            showConfirmDialog: Boolean(this.props.showConfirmDialogBeforeSending),
          })
        },
      })


    const DeleteButton = (
      <ButtonContainer key={1}>
        {Button}
        <RequestStatus status={this.state.requestStatus} errorMessage={this.state.requestErrorMessage} />
      </ButtonContainer>)

    const ConfirmDialog = this.state.isConfirmDialogVisible ?
      <Confirm
        key={2}
        content={this.props.showConfirmDialogBeforeSending}
        open={this.state.isConfirmDialogVisible}
        onConfirm={this.performAction}
        onCancel={() => this.setState({ isConfirmDialogVisible: false })}
      />
      : null

    return [
      DeleteButton,
      ConfirmDialog,
    ]
  }

  handleButtonClick = ({ showConfirmDialog } = {}) => {
    if (showConfirmDialog) {
      this.setState({ isConfirmDialogVisible: true })
    } else {
      this.performAction()
    }
  }

  performAction = () => {
    this.setState({ isConfirmDialogVisible: false, requestStatus: RequestStatus.IN_PROGRESS })

    this.httpRequestHelper = new HttpRequestHelper(
      this.props.requestUrl,
      this.handleRequestSuccess,
      this.handleRequestError,
      this.handleReset,
    )

    this.httpRequestHelper.post(this.props.getDataToSend())
  }

  handleRequestSuccess = (responseJson) => {
    if (this.props.onRequestSuccess) {
      this.props.onRequestSuccess(responseJson)
    }

    this.setState({ requestStatus: RequestStatus.SUCCEEDED })
  }

  handleRequestError = (error) => {
    if (this.props.onRequestError) {
      this.props.onRequestError(error)
    }

    //if deleteRequestStatus === RequestStatus.NONE, the status indicator has already been reset
    if (this.state.requestStatus !== RequestStatus.NONE) {
      this.setState({ requestStatus: RequestStatus.ERROR, requestErrorMessage: error.message.toString() })
    }

    console.log('ERROR', error)
  }

  handleReset = () => {
    this.setState({ requestStatus: RequestStatus.NONE, requestErrorMessage: null })
  }
}

export default SendRequestButton

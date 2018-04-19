import React from 'react'
import PropTypes from 'prop-types'
import { Confirm } from 'semantic-ui-react'

import RequestStatus from '../form/RequestStatus'


class DispatchRequestButton extends React.Component {

  static propTypes = {

    /** React component to show */
    buttonContent: PropTypes.node.isRequired,

    /** Callback to dispatch on submit */
    onSubmit: PropTypes.func.isRequired,

    /** Optional confirm dialog to show before submitting the request */
    confirmDialog: PropTypes.string,

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
    return (
      <span>
        <a role="button" onClick={this.handleButtonClick} tabIndex="0">
          {this.props.buttonContent}
        </a>
        <RequestStatus status={this.state.requestStatus} errorMessage={this.state.requestErrorMessage} />
        <Confirm
          content={this.props.confirmDialog}
          open={this.state.isConfirmDialogVisible}
          onConfirm={this.performAction}
          onCancel={() => this.setState({ isConfirmDialogVisible: false })}
        />
      </span>
    )
  }

  handleButtonClick = () => {
    if (this.props.confirmDialog) {
      this.setState({ isConfirmDialogVisible: true })
    } else {
      this.performAction()
    }
  }

  performAction = () => {
    this.setState({ isConfirmDialogVisible: false, requestStatus: RequestStatus.IN_PROGRESS })

    const dispatch = this.props.onSubmit()
    dispatch.onClear = this.handleReset
    dispatch.then(
      this.handleRequestSuccess,
      this.handleRequestError,
    )
  }

  handleRequestSuccess = () => {
    this.setState({ requestStatus: RequestStatus.SUCCEEDED })
  }

  handleRequestError = (error) => {
    //if deleteRequestStatus === RequestStatus.NONE, the status indicator has already been reset
    if (this.state.requestStatus !== RequestStatus.NONE) {
      this.setState({ requestStatus: RequestStatus.ERROR, requestErrorMessage: error.errors._error[0] || error.message }) //eslint-disable-line no-underscore-dangle
    }
  }

  handleReset = () => {
    this.setState({ requestStatus: RequestStatus.NONE, requestErrorMessage: null })
  }
}

export default DispatchRequestButton

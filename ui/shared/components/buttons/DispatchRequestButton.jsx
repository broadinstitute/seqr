import React from 'react'
import PropTypes from 'prop-types'
import { Confirm } from 'semantic-ui-react'

import RequestStatus from '../form/RequestStatus'
import { ButtonLink } from '../StyledComponents'


class DispatchRequestButton extends React.PureComponent {

  static propTypes = {

    /** React component to show if no children */
    buttonContent: PropTypes.node,

    /** Callback to dispatch on submit */
    onSubmit: PropTypes.func.isRequired,

    /** Optional confirm dialog to show before submitting the request */
    confirmDialog: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),

    /** child componenets */
    children: PropTypes.node,

    buttonContainer: PropTypes.node,

    /** Optional callback when request succeeds **/
    onSuccess: PropTypes.func,
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
    const { buttonContainer, buttonContent, confirmDialog, children, onSuccess, onSubmit, ...props } = this.props
    return React.cloneElement(buttonContainer || <span />, { children: [
      children ?
        React.cloneElement(children, { onClick: this.handleButtonClick, key: 'button' }) :
        <ButtonLink key="button" onClick={this.handleButtonClick} content={buttonContent} {...props} />,
      <RequestStatus key="status" status={this.state.requestStatus} errorMessage={this.state.requestErrorMessage} />,
      <Confirm
        key="confirm"
        content={confirmDialog}
        open={this.state.isConfirmDialogVisible}
        onConfirm={this.performAction}
        onCancel={() => this.setState({ isConfirmDialogVisible: false })}
      />,
    ] })
  }

  handleButtonClick = (event) => {
    event.preventDefault()
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
    if (this.props.onSuccess) {
      this.props.onSuccess()
    }
  }

  handleRequestError = (error) => {
    //if deleteRequestStatus === RequestStatus.NONE, the status indicator has already been reset
    if (this.state.requestStatus !== RequestStatus.NONE) {
      this.setState({ requestStatus: RequestStatus.ERROR, requestErrorMessage: ((error.errors || {})._error || [])[0] || error.message }) //eslint-disable-line no-underscore-dangle
    }
  }

  handleReset = () => {
    this.setState({ requestStatus: RequestStatus.NONE, requestErrorMessage: null })
  }
}

export default DispatchRequestButton

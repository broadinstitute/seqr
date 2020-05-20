import React from 'react'
import PropTypes from 'prop-types'
import { Confirm } from 'semantic-ui-react'

import RequestStatus, { NONE, SUCCEEDED, ERROR, IN_PROGRESS } from '../panel/RequestStatus'
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

    hideNoRequestStatus: PropTypes.bool,
  }

  constructor(props) {
    super(props)

    this.state = {
      requestStatus: NONE,
      requestErrorMessage: null,
      isConfirmDialogVisible: false,
    }
  }

  render() {
    const { buttonContainer, buttonContent, confirmDialog, children, onSuccess, onSubmit, hideNoRequestStatus, ...props } = this.props
    return React.cloneElement(buttonContainer || <span />, { children: [
      children ?
        React.cloneElement(children, { onClick: this.handleButtonClick, key: 'button' }) :
        <ButtonLink key="button" onClick={this.handleButtonClick} content={buttonContent} {...props} />,
      (!hideNoRequestStatus || this.state.requestStatus !== NONE) ?
        <RequestStatus key="status" status={this.state.requestStatus} errorMessage={this.state.requestErrorMessage} />
        : null,
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
    this.setState({ isConfirmDialogVisible: false, requestStatus: IN_PROGRESS })

    const dispatch = this.props.onSubmit()
    dispatch.onClear = this.handleReset
    dispatch.then(
      this.handleRequestSuccess,
      this.handleRequestError,
    )
  }

  handleRequestSuccess = () => {
    this.setState({ requestStatus: SUCCEEDED })
    if (this.props.onSuccess) {
      this.props.onSuccess()
    }
  }

  handleRequestError = (error) => {
    if (this.state.requestStatus !== NONE) {
      this.setState({ requestStatus: ERROR, requestErrorMessage: ((error.errors || {})._error || [])[0] || error.message }) //eslint-disable-line no-underscore-dangle
    }
  }

  handleReset = () => {
    this.setState({ requestStatus: NONE, requestErrorMessage: null })
  }
}

export default DispatchRequestButton

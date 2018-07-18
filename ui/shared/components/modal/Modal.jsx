import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Modal, Icon, Popup, Confirm } from 'semantic-ui-react'

import { getModalOpen, getModalConfim, openModal, closeModal, cancelCloseModal } from 'redux/utils/modalReducer'
import ButtonLink from '../buttons/ButtonLink'

class CustomModal extends React.Component
{
  static propTypes = {
    trigger: PropTypes.node,
    popup: PropTypes.object,
    title: PropTypes.string.isRequired,
    modalName: PropTypes.string.isRequired,
    handleClose: PropTypes.func,
    size: PropTypes.oneOf(['small', 'large', 'fullscreen']),
    isOpen: PropTypes.bool,
    confirmContent: PropTypes.string,
    open: PropTypes.func,
    close: PropTypes.func,
    cancelClose: PropTypes.func,
    children: PropTypes.node,
  }

  static defaultProps = {
    size: 'small',
  }

  handleClose = () => {
    this.props.close()
    if (this.props.handleClose) {
      this.props.handleClose()
    }
  }

  render() {
    let trigger = this.props.trigger ? React.cloneElement(this.props.trigger, { onClick: this.props.open }) : null
    if (this.props.popup) {
      trigger = <Popup trigger={trigger} {...this.props.popup} />
    }
    return (
      <Modal open={this.props.isOpen} trigger={trigger} onClose={this.handleClose} size={this.props.size}>
        <Modal.Header>
          {this.props.title}
          <ButtonLink float="right" onClick={this.handleClose}>
            <Icon name="remove" color="grey" size="small" />
          </ButtonLink>
        </Modal.Header>
        <Modal.Content>
          {this.props.children}
        </Modal.Content>
        <Confirm
          content={this.props.confirmContent}
          open={this.props.confirmContent != null}
          onCancel={this.props.cancelClose}
          onConfirm={() => this.props.close(true)}
        />
      </Modal>
    )
  }
}

const mapStateToProps = (state, ownProps) => ({
  isOpen: getModalOpen(state, ownProps.modalName),
  confirmContent: getModalConfim(state, ownProps.modalName),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    open: () => {
      dispatch(openModal(ownProps.modalName))
    },
    close: (confirm) => {
      dispatch(closeModal(ownProps.modalName, confirm))
    },
    cancelClose: () => {
      dispatch(cancelCloseModal(ownProps.modalName))
    },
  }
}

export { CustomModal as ModalComponent }

export default connect(mapStateToProps, mapDispatchToProps)(CustomModal)

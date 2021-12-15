import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Modal, Icon, Popup, Confirm } from 'semantic-ui-react'

import { getModalOpen, getModalConfim, openModal, closeModal, cancelCloseModal } from 'redux/utils/modalReducer'
import { ButtonLink } from '../StyledComponents'

class CustomModal extends React.PureComponent {

  static propTypes = {
    trigger: PropTypes.node,
    popup: PropTypes.object,
    title: PropTypes.string,
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
    const { close, handleClose } = this.props
    close()
    if (handleClose) {
      handleClose()
    }
  }

  confirmClose = () => {
    const { close } = this.props
    close(true)
  }

  render() {
    const {
      trigger: triggerProp, popup, open, isOpen, size, title, children, confirmContent, cancelClose,
    } = this.props
    let trigger = triggerProp ? React.cloneElement(triggerProp, { onClick: open }) : null
    if (popup) {
      trigger = <Popup trigger={trigger} {...popup} />
    }
    return (
      <Modal open={isOpen} trigger={trigger} onClose={this.handleClose} size={size}>
        <Modal.Header>
          {title}
          <ButtonLink floated="right" onClick={this.handleClose} icon={<Icon name="remove" color="grey" />} />
        </Modal.Header>
        <Modal.Content>
          {children}
        </Modal.Content>
        <Confirm
          content={confirmContent}
          open={confirmContent != null}
          onCancel={cancelClose}
          onConfirm={this.confirmClose}
        />
      </Modal>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  isOpen: getModalOpen(state, ownProps.modalName),
  confirmContent: getModalConfim(state, ownProps.modalName),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  open: (e) => {
    e.preventDefault()
    dispatch(openModal(ownProps.modalName))
  },
  close: (confirm) => {
    dispatch(closeModal(ownProps.modalName, confirm))
  },
  cancelClose: () => {
    dispatch(cancelCloseModal(ownProps.modalName))
  },
})

export { CustomModal as ModalComponent }

export default connect(mapStateToProps, mapDispatchToProps)(CustomModal)

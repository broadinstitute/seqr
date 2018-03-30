import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Modal, Icon, Popup } from 'semantic-ui-react'

import { getModalOpen, openModal, closeModal } from 'redux/utils/modalReducer'

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
    open: PropTypes.func,
    close: PropTypes.func,
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
          <span style={{ fontSize: '15px' }}>{this.props.title}</span>
          <a role="button" tabIndex="0" style={{ float: 'right', cursor: 'pointer' }} onClick={this.handleClose}>
            <Icon name="remove" style={{ fontSize: '15px', color: '#A3A3A3' }} />
          </a>
        </Modal.Header>
        <Modal.Content>
          {this.props.children}
        </Modal.Content>
      </Modal>
    )
  }
}

const mapStateToProps = (state, ownProps) => ({
  isOpen: getModalOpen(state, ownProps.modalName),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    open: () => {
      dispatch(openModal(ownProps.modalName))
    },
    close: () => {
      dispatch(closeModal(ownProps.modalName))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(CustomModal)

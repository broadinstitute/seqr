import React from 'react'
import PropTypes from 'prop-types'

import { Modal, Icon, Popup } from 'semantic-ui-react'


class CustomModal extends React.Component
{
  static propTypes = {
    trigger: PropTypes.node,
    popup: PropTypes.object,
    title: PropTypes.string.isRequired,
    handleClose: PropTypes.func,
    size: PropTypes.oneOf(['small', 'large', 'fullscreen']),
    children: PropTypes.node,
  }

  static defaultProps = {
    size: 'small',
  }

  state = {
    modalOpen: !this.props.trigger,
  }

  handleOpen = () => this.setState({ modalOpen: true })

  handleClose = () => {
    if (this.props.handleClose) {
      this.props.handleClose()
    } else {
      this.setState({ modalOpen: false })
    }
  }

  render() {
    const children = this.props.children ? React.cloneElement(this.props.children, { handleClose: this.handleClose }) : null
    let trigger = this.props.trigger ? React.cloneElement(this.props.trigger, { onClick: this.handleOpen }) : null
    if (this.props.popup) {
      trigger = <Popup trigger={trigger} {...this.props.popup} />
    }
    return (
      <Modal open={this.state.modalOpen} trigger={trigger} onClose={this.handleClose} size={this.props.size}>
        <Modal.Header>
          <span style={{ fontSize: '15px' }}>{this.props.title}</span>
          <a role="button" tabIndex="0" style={{ float: 'right', cursor: 'pointer' }} onClick={this.handleClose}>
            <Icon name="remove" style={{ fontSize: '15px', color: '#A3A3A3' }} />
          </a>
        </Modal.Header>
        <Modal.Content style={{ textAlign: 'center' }}>
          {children}
        </Modal.Content>
      </Modal>
    )
  }
}

export default CustomModal

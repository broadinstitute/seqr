import React from 'react'
import Modal from './Modal'

class ModalWithIFrame extends React.Component
{
  static propTypes = {
    title: React.PropTypes.string.isRequired,
    url: React.PropTypes.string.isRequired,
    onClose: React.PropTypes.func,
  }

  render() {
    return <Modal title={this.props.title} onClose={this.props.onClose}>
      <iframe src={this.props.url} />
    </Modal>
  }
}


export default ModalWithIFrame

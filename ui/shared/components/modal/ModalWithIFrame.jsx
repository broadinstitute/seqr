import React from 'react'
import PropTypes from 'prop-types'

import Modal from './Modal'

class ModalWithIFrame extends React.Component
{
  static propTypes = {
    title: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    onClose: PropTypes.func,
  }

  render() {
    return (
      <Modal title={this.props.title} onClose={this.props.onClose}>
        <iframe src={this.props.url} />
      </Modal>)
  }
}


export default ModalWithIFrame

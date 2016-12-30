import React from 'react'

import { Modal, Icon } from 'semantic-ui-react'

const CustomModal = ({ title, onClose, children, size = 'small' }) =>
  <Modal open onClose={onClose} size={size}>
    <Modal.Header>
      <span style={{ fontSize: '17px' }}>{title}</span>
      <a tabIndex="0" style={{ float: 'right', cursor: 'pointer' }} onClick={onClose}>
        <Icon name="remove" style={{ fontSize: '15px', color: '#A3A3A3' }} />
      </a>
    </Modal.Header>
    <Modal.Content style={{ textAlign: 'center' }}>
      {children}
    </Modal.Content>
  </Modal>

CustomModal.propTypes = {
  title: React.PropTypes.string.isRequired,
  onClose: React.PropTypes.func.isRequired,
  children: React.PropTypes.element.isRequired,
  size: React.PropTypes.oneOf(['small', 'large', 'fullscreen']),
}

export default CustomModal

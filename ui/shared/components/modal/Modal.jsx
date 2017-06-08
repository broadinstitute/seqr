import React from 'react'
import PropTypes from 'prop-types'

import { Modal, Icon } from 'semantic-ui-react'

const CustomModal = ({ title, onClose, children, size = 'small' }) =>
  <Modal open onClose={onClose} size={size}>
    <Modal.Header>
      <span style={{ fontSize: '15px' }}>{title}</span>
      <a tabIndex="0" style={{ float: 'right', cursor: 'pointer' }} onClick={onClose}>
        <Icon name="remove" style={{ fontSize: '15px', color: '#A3A3A3' }} />
      </a>
    </Modal.Header>
    <Modal.Content style={{ textAlign: 'center' }}>
      {children}
    </Modal.Content>
  </Modal>

CustomModal.propTypes = {
  title: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  size: PropTypes.oneOf(['small', 'large', 'fullscreen']),
  children: PropTypes.node,
}

export default CustomModal

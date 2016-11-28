import React from 'react'

import { Modal, Icon } from 'semantic-ui-react'

const ModalWithButtons = (props) => {
  return <Modal open onClose={props.onClose} size={props.size}>
    <Modal.Header>
      <span style={{ fontSize: '17px' }}>{props.title}</span>
      <a tabIndex="0" style={{ float: 'right', cursor: 'pointer' }} onClick={props.onClose}>
        <Icon name="remove" style={{ fontSize: '15px', color: '#A3A3A3' }} />
      </a>
    </Modal.Header>
    <Modal.Content style={{ textAlign: 'center' }}>
      {props.children}
    </Modal.Content>
  </Modal>
}

ModalWithButtons.propTypes = {
  title: React.PropTypes.string.isRequired,
  onClose: React.PropTypes.func.isRequired,
  children: React.PropTypes.element.isRequired,
  size: React.PropTypes.oneOf(['small', 'large', 'fullscreen']),
}

export default ModalWithButtons

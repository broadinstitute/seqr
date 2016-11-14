import React from 'react'

import {Modal, Icon} from 'semantic-ui-react'

const CustomModal = ({title, onClose, children}) =>
    <Modal open={true} onClose={onClose} size="small">
        <Modal.Header>
            {title}
            <span style={{float: "right", cursor: "pointer"}} onClick={onClose}>
                  <Icon name="remove" style={{fontSize: "15px", color: "#A3A3A3"}} />
            </span>
        </Modal.Header>
        <Modal.Content style={{textAlign:"center"}}>
            {children}
        </Modal.Content>
    </Modal>

CustomModal.propTypes = {
    title: React.PropTypes.string.isRequired,
    onClose: React.PropTypes.func.isRequired,
    children: React.PropTypes.element.isRequired
}


export default CustomModal
import React from 'react'

const ModalWithButtons = ({title, children, onClose, onOkClick = (event) => {} }) => {
    return <Modal {...{title, children, onClose}}>
        <div style={{padding:"20px"}}>
            {children}
        </div>
        <div className="actions" style={{height:"55px"}}>
            <div className="ui button" style={{padding:"7px 15px 7px 15px"}} onClick={onClose}>Cancel</div>
            <div className="ui button" style={{padding:"7px 15px 7px 15px"}} onClick={onOkClick}>OK</div>
        </div>

    </Modal>
}

export default ModalWithButtons
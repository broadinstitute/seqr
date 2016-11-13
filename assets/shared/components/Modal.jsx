import React from 'react'

const Modal = ({title, children, showButtons=true, okClickHandler=(event) => {} }) => {
    return <div className="ui active modal" style={{width: null, height:null}}>
        <div className="header" style={{padding:"7px 5px 7px 20px"}}>
            <span style={{fontSize:"12pt"}}>{title} &nbsp; Test </span>
            <span style={{position:"absolute", right:"12px"}}>
                <i className="close icon" style={{fontSize:"15px", color:"#A3A3A3"}}></i>
            </span>
        </div>
        <div style={{padding:"20px"}}>
            {children}
        </div>
        {showButtons ?
            <div className="actions" style={{height:"55px"}}>
                <div className="ui button" style={{padding:"7px 15px 7px 15px"}}>Cancel</div>
                <div className="ui button" style={{padding:"7px 15px 7px 15px"}} onClick={okClickHandler}>OK</div>
            </div> :
            null
        }
    </div>
}

export default Modal
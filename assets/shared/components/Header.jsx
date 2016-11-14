import React from 'react'

module.exports = React.createClass({
    getInitialState: function () {

        return window.initialJSON;
    },

    render: function () {
        return <div className="ui vertical segment" style={{
                        backgroundColor:"#F3F3F3",
                        borderStyle:'solid',
                        borderWidth:"0px 0px 1px 0px",
                        borderColor:'#E2E2E2'
                    }}>
            <div className="ui grid" style={{color:'#272727'}}>
                <div className="one wide column"></div>
                <div className="column" style={{fontSize: 16, fontFamily: 'sans-serif', fontWeight: 400}}>
                    <a href="/"><i>seqr</i></a>
                </div>
                <div className="five wide column"> { /*
                    <div className="ui input" style={{height:"10px", width:"330px"}}>
                        <input type="text" placeholder="Project, Gene, Tag ..." />
                    </div>
                 */ }
                </div>
                <div className="five wide column" style={{textAlign: "right", fontWeight: 400}}>
                    Logged in as <b>{this.state ? (this.state.user.email || this.state.user.username) : null}</b>
                </div>
                <div className="two wide column" style={{textAlign: "right"}}>
                    <a href="/logout">Log out</a>
                </div>
                <div className="one wide column"></div>
            </div>
        </div>
    }
})
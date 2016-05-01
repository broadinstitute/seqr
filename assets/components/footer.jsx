import React from 'react'

module.exports = React.createClass({

    render: function () {

        return <div className="ui grid" style={{
                    backgroundColor: "#F3F3F3",
                    borderStyle:'solid',
                    borderWidth:"1px 0px 0px 0px",
                    borderColor:'#E2E2E2' }}>

            <div className="two wide column"></div>
            <div className="seven wide column">
                For bug reports or feature requests please submit  &nbsp;
                <a href="https://github.com/macarthur-lab/seqr/issues">Github Issues</a>
            </div>
            <div className="five wide column" style={{textAlign:"right", paddingTop: "10px", paddingBottom: "10px"}}>
                If you have questions or feedback, &nbsp;
                <a href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;tf=1&amp;to=seqr@broadinstitute.org" target="_blank">Contact Us</a>
            </div>
            <div className="two wide column"></div>
        </div>

    }
})


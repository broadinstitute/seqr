import React from 'react';

module.exports = React.createClass({

    render: function () {
        return <div style={{marginBottom: "10px"}}>
            {
                this.props.breadcrumbs.map((label, i) => {
                    return <span key={i} className="ui large breadcrumb">{
                        i < this.props.breadcrumbs.length - 1 ?
                            (<div><span style={{marginRight: "10px"}}>{this.props.breadcrumbs[i]}</span> {'»'}</div>) :
                            (<div style={{marginLeft: "10px"}} className="active section">{this.props.breadcrumbs[i]}</div>)
                    }</span>
                })
            }
        </div>
    },
    
});

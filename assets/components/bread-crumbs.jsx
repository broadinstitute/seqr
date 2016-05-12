import React from 'react';

module.exports = React.createClass({

    render: function () {
        return <div className="ui large breadcrumb">
            <div className="active section">{this.props.breadcrumbs[0]}</div>
        </div>
    }
});

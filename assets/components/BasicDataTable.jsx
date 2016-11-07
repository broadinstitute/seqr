/*eslint-env jquery */

import React from 'react';
import './css/BasicDataTable.css';

module.exports = React.createClass({
    propTypes: {
        title: React.PropTypes.string.isRequired,
    },

    getDefaultProps: function() {
        return {
            page_length: 20,
        };
    },

    render: function() {

        return <table className="ui celled table basic-data-table ${this.properties.className}" style={{width:"100%"}}>
            {this.props.children}
        </table>;
    },

    componentDidMount: function() {

        /** set options  (www.datatables.net/reference/options) */
        let default_options = {
            processing: true,  /* display of a 'processing' indicator when the table is being processed e.g. during a sort (datatables.net/reference/option/processing) */
            paging: true,
            pageLength: this.props.page_length,    /* default page length */
            lengthChange: false,  /* show rows-per-page selector (datatables.net/reference/option/lengthChange) */
            dom: 'l<"#basic-data-table-find" f>rti<"#basic-data-table-pager" p>',  //"dom": '<"top"i>rt<"bottom"flp><"clear">'};
            autoWidth: true,  /* automatic column width calculation. default: true */
        };

        //init the datatable
        $('.basic-data-table').DataTable(default_options);

        $('#basic-data-table-find').append("<h4>"+this.props.title+"</h4>");

        if(this.props.children && this.props.children.length < this.props.page_length) {
            $('#basic-data-table-pager').hide();
        }
    },
});



///* eslint-disable */

import React from 'react'
import $ from 'jquery'
import DataTablesLib from 'datatables.net'

import './datatable.css'

$.DataTable = DataTablesLib


class DataTable extends React.Component
{
  constructor() {
    super()

    this.dataTableRef = null
  }

  componentDidMount() {
    $(this.dataTableRef).DataTable({
      dom: '<"data-table-wrapper"t>',
      ...this.props.config,
    })
  }

  componentWillUnmount() {
    $('.data-table-wrapper')
      .find('table')
      .DataTable()
      .destroy(true)
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return <div>
      <table ref={this.handleDataTableRef} />
    </div>
  }

  handleDataTableRef(ref) {
    if (!ref) {
      return
    }

    this.dataTableRef = ref
  }
}


DataTable.propTypes = {
  config: React.PropTypes.object.isRequired,
}

export default DataTable

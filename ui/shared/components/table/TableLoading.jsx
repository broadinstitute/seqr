import React from 'react'
import PropTypes from 'prop-types'
import { Table, Loader } from 'semantic-ui-react'

const TableLoading = ({ numCols }) =>
  <Table.Row>
    <Table.Cell colSpan={numCols || '12'}><Loader inline="centered" active /></Table.Cell>
  </Table.Row>

TableLoading.propTypes = {
  numCols: PropTypes.number,
}

export default TableLoading

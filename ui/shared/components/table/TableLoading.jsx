import React from 'react'
import PropTypes from 'prop-types'
import { Table, Loader } from 'semantic-ui-react'

const TableLoading = ({ numCols, inline = 'centered' }) =>
  <Table.Row>
    <Table.Cell colSpan={numCols || '12'}><Loader inline={inline} active /></Table.Cell>
  </Table.Row>

TableLoading.propTypes = {
  numCols: PropTypes.number,
  inline: PropTypes.any,
}

export default TableLoading

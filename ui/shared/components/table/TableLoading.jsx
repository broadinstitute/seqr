import React from 'react'
import PropTypes from 'prop-types'
import { Table, Loader, Dimmer } from 'semantic-ui-react'

const TableLoading = ({ numCols, inline = 'centered' }) =>
  <Table.Row>
    <Table.Cell colSpan={numCols || '12'}>
      {/*Loader needs to be in an extra Dimmer to properly show up if it is in a modal (https://github.com/Semantic-Org/Semantic-UI-React/issues/879)*/}
      <Dimmer inverted active><Loader inline={inline} active /></Dimmer>
    </Table.Cell>
  </Table.Row>

TableLoading.propTypes = {
  numCols: PropTypes.number,
  inline: PropTypes.any,
}

export default TableLoading

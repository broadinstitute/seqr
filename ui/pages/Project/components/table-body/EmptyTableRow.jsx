import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import { getFamiliesFilter } from '../../redux/rootReducer'
import { SHOW_ALL } from '../../constants'

const EmptyTableRow = ({ familiesFilter }) =>
  <Table.Row>
    <Table.Cell style={{ padding: '10px 0px 10px 15px', color: 'gray', borderWidth: '0px' }}>
      0 families
      { familiesFilter !== SHOW_ALL ? ' in this category' : ' in this project' }
    </Table.Cell>
  </Table.Row>

export { EmptyTableRow as EmptyTableRowComponent }

EmptyTableRow.propTypes = {
  familiesFilter: PropTypes.string.isRequired,
}

const mapStateToProps = state => ({
  familiesFilter: getFamiliesFilter(state),
})

export default connect(mapStateToProps)(EmptyTableRow)

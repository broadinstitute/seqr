import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import { SHOW_ALL } from 'shared/utils/constants'
import { getFamiliesFilter } from '../../selectors'
import { FAMILY_FILTER_LOOKUP } from '../../constants'

const EmptyCell = styled(Table.Cell)`
  padding: 10px 0px 10px 15px;
  color: gray;
  border-width: 0px;
`

const EmptyTableRow = ({ familiesFilter }) =>
  <Table.Row>
    <EmptyCell>
      0 families
      { familiesFilter !== SHOW_ALL ? ` with filter "${FAMILY_FILTER_LOOKUP[familiesFilter].name}"` : ' in this project' }
    </EmptyCell>
  </Table.Row>

export { EmptyTableRow as EmptyTableRowComponent }

EmptyTableRow.propTypes = {
  familiesFilter: PropTypes.string.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  familiesFilter: getFamiliesFilter(state, ownProps),
})

export default connect(mapStateToProps)(EmptyTableRow)

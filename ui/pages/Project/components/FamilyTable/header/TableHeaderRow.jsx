import React from 'react'
import { Table } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'

import { getProjectFamilies, getVisibleFamilies } from '../../../selectors'

import FamiliesFilterDropdown from './FilterDropdown'
import FamiliesFilterSearchBox from './FilterSearchBox'
import FamiliesSortOrderDropdown from './SortOrderDropdown'
import SortDirectionToggle from './SortDirectionToggle'

const RegularFontHeaderCell = styled(Table.HeaderCell)`
  font-weight: normal !important;
`

const TableHeaderRow = ({ headerStatus, showInternalFilters, visibleFamiliesCount, totalFamiliesCount }) =>
  <Table.Header fullWidth>
    <Table.Row>
      <RegularFontHeaderCell>
        Showing &nbsp;
        {
          visibleFamiliesCount !== totalFamiliesCount ?
            <span><b>{visibleFamiliesCount}</b> out of <b>{totalFamiliesCount}</b></span>
            : <span>all <b>{totalFamiliesCount}</b></span>
        }
        &nbsp; families
      </RegularFontHeaderCell>
      <Table.HeaderCell collapsing textAlign="right">
        <FamiliesFilterSearchBox />
      </Table.HeaderCell>
      <Table.HeaderCell collapsing textAlign="right">
        <FamiliesSortOrderDropdown />
        <HorizontalSpacer width={5} />
        <SortDirectionToggle />
      </Table.HeaderCell>
      <Table.HeaderCell collapsing textAlign="right">
        Status: <FamiliesFilterDropdown showInternalFilters={showInternalFilters} />
      </Table.HeaderCell>
      {headerStatus &&
        <Table.HeaderCell collapsing textAlign="right">
          {headerStatus.title}:
          <HorizontalSpacer width={10} />
          <HorizontalStackedBar
            width={100}
            height={14}
            title={headerStatus.title}
            data={headerStatus.data}
          />
        </Table.HeaderCell>
      }
    </Table.Row>
  </Table.Header>

TableHeaderRow.propTypes = {
  headerStatus: PropTypes.object,
  showInternalFilters: PropTypes.bool,
  visibleFamiliesCount: PropTypes.number,
  totalFamiliesCount: PropTypes.number,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamiliesCount: getVisibleFamilies(state, ownProps).length,
  totalFamiliesCount: getProjectFamilies(state).length,
})


export { TableHeaderRow as TableHeaderRowComponent }

export default withRouter(connect(mapStateToProps)(TableHeaderRow))

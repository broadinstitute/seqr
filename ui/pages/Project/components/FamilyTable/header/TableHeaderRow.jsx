import React from 'react'
import { Grid, Table } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'

import { getProjectTablePage, getProjectTableRecordsPerPage } from '../../../reducers'
import { getProjectFamilies, getVisibleFamilies } from '../../../utils/selectors'

import FamiliesFilterDropdown from './FilterDropdown'
import FamiliesSortOrderDropdown from './SortOrderDropdown'
import SortDirectionToggle from './SortDirectionToggle'
import ShowDetailsToggle from './ShowDetailsToggle'


const TableHeaderRow = ({ headerStatus, showInternalFilters, visibleFamiliesCount, totalFamiliesCount, currentPage, recordsPerPage }) =>
  <Table.Header fullWidth>
    <Table.Row>
      <Table.HeaderCell>
        <Grid stackable>
          <Grid.Column width={6}>
            <span style={{ fontWeight: 'normal' }}>
              Showing &nbsp;
              {
                visibleFamiliesCount !== totalFamiliesCount ?
                  <span><b>{((currentPage - 1) * recordsPerPage) + 1}-{((currentPage - 1) * recordsPerPage) + visibleFamiliesCount}</b> out of <b>{totalFamiliesCount}</b></span>
                  : <span>all <b>{totalFamiliesCount}</b></span>
              }
              &nbsp; families
            </span>
            <FamiliesFilterDropdown showInternalFilters={showInternalFilters} />
          </Grid.Column>
          <Grid.Column width={3}>
            <div style={{ whitespace: 'nowrap' }}>
              <FamiliesSortOrderDropdown />
              <HorizontalSpacer width={5} />
              <SortDirectionToggle />
            </div>
          </Grid.Column>
          <Grid.Column width={3}>
            <ShowDetailsToggle />
          </Grid.Column>
          <Grid.Column width={4}>
            {headerStatus &&
              <span style={{ float: 'right' }}>
                {headerStatus.title}:
                <HorizontalSpacer width={10} />
                <HorizontalStackedBar
                  width={100}
                  height={10}
                  title={headerStatus.title}
                  data={headerStatus.data}
                />
              </span>
            }
          </Grid.Column>

        </Grid>
      </Table.HeaderCell>
    </Table.Row>
  </Table.Header>

TableHeaderRow.propTypes = {
  headerStatus: PropTypes.object,
  showInternalFilters: PropTypes.bool,
  visibleFamiliesCount: PropTypes.number,
  totalFamiliesCount: PropTypes.number,
  currentPage: PropTypes.number,
  recordsPerPage: PropTypes.number,
}

const mapStateToProps = state => ({
  currentPage: getProjectTablePage(state),
  recordsPerPage: getProjectTableRecordsPerPage(state),
  visibleFamiliesCount: getVisibleFamilies(state).length,
  totalFamiliesCount: getProjectFamilies(state).length,
})


export { TableHeaderRow as TableHeaderRowComponent }

export default connect(mapStateToProps)(TableHeaderRow)

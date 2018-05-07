import React from 'react'
import { Grid, Table } from 'semantic-ui-react'
import styled from 'styled-components'
import PropTypes from 'prop-types'

import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'

import FamiliesFilterDropdown from './FilterDropdown'
import FamiliesSortOrderDropdown from './SortOrderDropdown'
import PageSelector from './PageSelector'
import SortDirectionToggle from './SortDirectionToggle'
import ShowDetailsToggle from './ShowDetailsToggle'

const TableRow = styled(Table.Row)`
  background-color: #F3F3F3 !important;
`
const FamiliesFilterColumn = styled(Grid.Column)`
  min-width: 400px;
`

const FamiliesSortOrderColumn = styled(Grid.Column)`
  min-width: 300px;
`

const DetailsToggleColumn = styled(Grid.Column)`
  min-width: 170px;
`

const TableHeaderRow = ({ headerStatus, showInternalFilters }) =>
  <TableRow>
    <Table.Cell>
      <Grid stackable>
        <FamiliesFilterColumn width={5}>
          <PageSelector />
          <FamiliesFilterDropdown showInternalFilters={showInternalFilters} />
        </FamiliesFilterColumn>
        <FamiliesSortOrderColumn width={4}>
          <div style={{ whitespace: 'nowrap' }}>
            <FamiliesSortOrderDropdown />
            <HorizontalSpacer width={5} />
            <SortDirectionToggle />
          </div>
        </FamiliesSortOrderColumn>
        <DetailsToggleColumn width={2}>
          <ShowDetailsToggle />
        </DetailsToggleColumn>
        { headerStatus &&
          <Grid.Column width={4} floated="right">
            <b>{headerStatus.title}:</b>
            <HorizontalSpacer width={10} />
            <HorizontalStackedBar
              width={100}
              height={10}
              title={headerStatus.title}
              data={headerStatus.data}
            />
          </Grid.Column>
         }
      </Grid>
    </Table.Cell>
  </TableRow>

TableHeaderRow.propTypes = {
  headerStatus: PropTypes.object,
  showInternalFilters: PropTypes.bool,
}

export { TableHeaderRow as TableHeaderRowComponent }

export default TableHeaderRow

import React from 'react'
import { Grid, Table } from 'semantic-ui-react'
import styled from 'styled-components'
import { HorizontalSpacer } from 'shared/components/Spacers'

import FamiliesFilterDropdown from './FilterDropdown'
import FamiliesSortOrderDropdown from './SortOrderDropdown'
import PageSelector from './PageSelector'
import SortDirectionToggle from './SortDirectionToggle'
import ShowDetailsToggle from './ShowDetailsToggle'
//import StatusBarGraph from './StatusBarGraph'

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

const TableHeaderRow = () =>
  <TableRow>
    <Table.Cell>
      <Grid stackable>
        <FamiliesFilterColumn width={6}>
          <PageSelector />
          <FamiliesFilterDropdown />
        </FamiliesFilterColumn>
        <FamiliesSortOrderColumn width={5}>
          <div style={{ whitespace: 'nowrap' }}>
            <FamiliesSortOrderDropdown />
            <HorizontalSpacer width={5} />
            <SortDirectionToggle />
          </div>
        </FamiliesSortOrderColumn>
        <DetailsToggleColumn width={2}>
          <ShowDetailsToggle />
        </DetailsToggleColumn>
        {/*
        <Grid.Column width={5}>
          <StatusBarGraph />
        </Grid.Column>
        */}
      </Grid>
    </Table.Cell>
  </TableRow>

export { TableHeaderRow as TableHeaderRowComponent }

export default TableHeaderRow

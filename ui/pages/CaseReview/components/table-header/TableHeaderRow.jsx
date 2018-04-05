import React from 'react'
import { Grid, Table } from 'semantic-ui-react'
import styled from 'styled-components'
import { HorizontalSpacer } from 'shared/components/Spacers'

import FamiliesFilterDropdown from '../../../Project/components/FamilyTable/header/FilterDropdown'
import FamiliesSortOrderDropdown from '../../../Project/components/FamilyTable/header/SortOrderDropdown'
import PageSelector from '../../../Project/components/FamilyTable/header/PageSelector'
import SortDirectionToggle from '../../../Project/components/FamilyTable/header/SortDirectionToggle'
import ShowDetailsToggle from '../../../Project/components/FamilyTable/header/ShowDetailsToggle'
import StatusBarGraph from './StatusBarGraph'

const TableRow = styled(Table.Row)`
  background-color: #F3F3F3 !important;
`
const FamiliesFilterColumn = styled(Grid.Column)`
  min-width: 400px;
`

const FamiliesSortOrderColumn = styled(Grid.Column)`
  min-width: 270px;
`

const DetailsToggleColumn = styled(Grid.Column)`
  min-width: 170px;
`
//TODO create a shared component with the Project page.
const TableHeaderRow = () =>
  <TableRow>
    <Table.Cell>
      <Grid stackable>
        <FamiliesFilterColumn width={6}>
          <PageSelector />
          <FamiliesFilterDropdown />
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
        <Grid.Column width={4}>
          <StatusBarGraph />
        </Grid.Column>
      </Grid>
    </Table.Cell>
  </TableRow>

export { TableHeaderRow as TableHeaderRowComponent }

export default TableHeaderRow

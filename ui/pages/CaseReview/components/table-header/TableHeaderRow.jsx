import React from 'react'
import { Grid, Table } from 'semantic-ui-react'

import { HorizontalSpacer } from 'shared/components/Spacers'

import FamiliesFilterDropdown from './FilterDropdown'
import FamiliesSortOrderDropdown from './SortOrderDropdown'
import SortDirectionToggle from './SortDirectionToggle'
import ShowDetailsToggle from './ShowDetailsToggle'
import StatusBarGraph from './StatusBarGraph'

const TableHeaderRow = () =>
  <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
    <Table.Cell>
      <Grid stackable>
        <Grid.Column width={4}>
          <FamiliesFilterDropdown />
        </Grid.Column>
        <Grid.Column width={4}>
          <div style={{ whitespace: 'nowrap' }}>
            <FamiliesSortOrderDropdown />
            <HorizontalSpacer width={5} />
            <SortDirectionToggle />
          </div>
        </Grid.Column>

        <Grid.Column width={2} />

        <Grid.Column width={2}>
          <ShowDetailsToggle />
        </Grid.Column>
        <Grid.Column width={4}>
          <StatusBarGraph />
        </Grid.Column>
      </Grid>
    </Table.Cell>
  </Table.Row>

export { TableHeaderRow as TableHeaderRowComponent }

export default TableHeaderRow

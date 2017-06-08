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
        <Grid.Column className="table-header-column">
          <FamiliesFilterDropdown />
        </Grid.Column>
        <Grid.Column className="table-header-column">
          <div className="nowrap" style={{ display: 'block' }}>
            <FamiliesSortOrderDropdown />
            <HorizontalSpacer width={5} />
            <SortDirectionToggle />
          </div>
        </Grid.Column>

        <Grid.Column className="table-header-column" style={{ margin: '0 auto' }} />

        <Grid.Column className="table-header-column">
          <ShowDetailsToggle />
        </Grid.Column>
        <Grid.Column className="table-header-column">
          <StatusBarGraph />
        </Grid.Column>
      </Grid>
    </Table.Cell>
  </Table.Row>

export { TableHeaderRow as TableHeaderRowComponent }

export default TableHeaderRow

import React from 'react'
import { Grid, Table } from 'semantic-ui-react'
import FamiliesFilterDropdown from './FilterDropdown'
import FamiliesSortOrderDropdown from './SortOrderDropdown'
import SortDirectionToggle from './SortDirectionToggle'
import ShowDetailsToggle from './ShowDetailsToggle'
import StatusBarGraph from './StatusBarGraph'

import { HorizontalSpacer } from '../../../../shared/components/Spacers'

const TableHeaderRow = () =>
  <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
    <Table.Cell>
      <Grid stackable>
        <Grid.Column width={5}>
          <FamiliesFilterDropdown />
        </Grid.Column>
        <Grid.Column width={4}>
          <div className="nowrap">
            <FamiliesSortOrderDropdown />
            <HorizontalSpacer width={5} />
            <SortDirectionToggle />
          </div>
        </Grid.Column>
        <Grid.Column width={2}>
          <ShowDetailsToggle />
        </Grid.Column>
        <Grid.Column width={5}>
          <StatusBarGraph />
        </Grid.Column>
      </Grid>
    </Table.Cell>
  </Table.Row>


export default TableHeaderRow

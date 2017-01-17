import React from 'react'
import { Grid, Table } from 'semantic-ui-react'

import FilterSelector from './FilterSelector'
import SortOrderSelector from './SortOrderSelector'
import SortDirectionSelector from './SortDirectionSelector'

class ProjectsTableHeader extends React.PureComponent {

  render() {
    return <Table.Row style={{ backgroundColor: '#F3F3F3' /*'#D0D3DD'*/ }}>
      <Table.Cell>
        <Grid stackable>
          <Grid.Column width={4}>
            <FilterSelector />
          </Grid.Column>
          <Grid.Column width={9}>
            <SortOrderSelector />
            <SortDirectionSelector />
          </Grid.Column>
          {/*
          <Grid.Column width={4}>
            <ShowCategoriesToggle />
          </Grid.Column>
          */}
          <Grid.Column width={3} />
        </Grid>
      </Table.Cell>
    </Table.Row>
  }
}

export default ProjectsTableHeader

import React from 'react'
import { Grid } from 'semantic-ui-react'

import FilterSelector from './FilterSelector'
import SortOrderSelector from './SortOrderSelector'
import SortDirectionSelector from './SortDirectionSelector'
import ShowDetailsSelector from './ShowDetailsSelector'

class ProjectsTableHeader extends React.Component {

  render() {
    return <Grid stackable>
      <Grid.Column width={4}>
        <FilterSelector />
      </Grid.Column>
      <Grid.Column width={5}>
        <SortOrderSelector />
        <SortDirectionSelector />
      </Grid.Column>
      <Grid.Column width={4}>
        <ShowDetailsSelector />
      </Grid.Column>
      <Grid.Column width={3} />
    </Grid>
  }
}

export default ProjectsTableHeader

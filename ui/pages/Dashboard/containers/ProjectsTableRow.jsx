import React from 'react'
import { Grid } from 'semantic-ui-react'
import Timeago from 'timeago.js'

import CaseReviewLink from './CaseReviewLink'
import ProjectPageLink from './ProjectPageLink'
import { HorizontalSpacer } from '../../../shared/components/Spacers'
/*
import FilterSelector from './FilterSelector'
import SortOrderSelector from './SortOrderSelector'
import SortDirectionSelector from './SortDirectionSelector'
import ShowDetailsSelector from './ShowDetailsSelector'
*/

class ProjectsTableRow extends React.Component {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    projectGuid: React.PropTypes.string.isRequired,
    projectsByGuid: React.PropTypes.object.isRequired,
  }

  render() {
    const project = this.props.projectsByGuid[this.props.projectGuid]
    return <div style={{ paddingTop: '10px' }}>
      <Grid stackable>
        <Grid.Column width={5}>
          <ProjectPageLink project={project} />
          {
            this.props.user.is_staff &&
            (<span><br />
              <HorizontalSpacer width={10} /><CaseReviewLink projectGuid={project.projectGuid} />
            </span>)
          }
        </Grid.Column>
        <Grid.Column width={2}>
          <span style={{ color: 'gray' }}>
            {project.numFamilies} families
          </span>
        </Grid.Column>
        <Grid.Column width={6}>

          <span style={{ color: 'gray' }}>
            {project.numIndividuals} individuals
          </span>
        </Grid.Column>
        <Grid.Column width={3}>
          <div style={{ fontSize: '13px', color: 'gray' }}>
            CREATED {new Timeago().format(project.created_date).toUpperCase()}<br />
          </div>
        </Grid.Column>
      </Grid>
    </div>
  }
}

export default ProjectsTableRow

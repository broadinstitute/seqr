import React from 'react'
import { Grid, Icon, Table } from 'semantic-ui-react'
import Timeago from 'timeago.js'

import ProjectPageLink from './ProjectPageLink'
import EllipsisMenu from './ProjectEllipsisMenu'
import { HorizontalSpacer } from '../../../shared/components/Spacers'


class ProjectsTableRow extends React.PureComponent {

  static propTypes = {
    //user: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
  }

  shouldComponentUpdate(nextProps) {
    return this.props.project !== nextProps.project
  }

  render() {
    const project = this.props.project
    return <Table.Row>
      <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
        <div style={{ paddingTop: '10px', color: '#555555' }}>
          <Grid stackable>
            <Grid.Column width={5}>
              <b><Icon name="chevron right" size="small" style={{ color: '#55555' }} /></b>
              <ProjectPageLink project={project} />
              { project.description && (
                <span><HorizontalSpacer width={10} />{project.description}</span>
                )
              }
            </Grid.Column>
            <Grid.Column width={3}>
              <span style={{ color: 'gray' }}>
                {project.datasets && project.datasets.map(
                  d => `${d.isLoaded ? d.numSamples : d.numSamples}  ${d.sequencingType}`).join(', ')}
              </span>
            </Grid.Column>
            <Grid.Column width={2}>
              <span style={{ color: 'gray' }}>
                {project.numFamilies} families
              </span>
            </Grid.Column>
            <Grid.Column width={2}>
              <span style={{ color: 'gray' }}>
                {project.numIndividuals} individ.
              </span>
            </Grid.Column>
            <Grid.Column width={4}>
              <div style={{ fontSize: '13px', color: 'gray' }}>
                created {new Timeago().format(project.createdDate)}
                <span style={{ float: 'right' }}>
                  <EllipsisMenu projectGuid={project.projectGuid} />
                </span>
              </div>
            </Grid.Column>
          </Grid>
        </div>
      </Table.Cell>
    </Table.Row>
  }
}

export default ProjectsTableRow

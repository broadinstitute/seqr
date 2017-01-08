/* eslint no-undef: "warn" */
import React from 'react'
import { Button, Grid, Table } from 'semantic-ui-react'

import CaseReviewLink from './CaseReviewLink'


class ProjectsTable extends React.Component {

  static propTypes = {
    projectsByGuid: React.PropTypes.object.isRequired,
  }

  render() {
    const {
      projectsByGuid,
    } = this.props

    return <Table celled striped style={{ width: '100%' }}>
      <Table.Header>
        <Table.Row>
          <Table.HeaderCell collapsing>Projects</Table.HeaderCell>
          <Table.HeaderCell>. </Table.HeaderCell>
          <Table.HeaderCell collapsing>Created</Table.HeaderCell>
          <Table.HeaderCell collapsing>Accessed</Table.HeaderCell>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {
          Object.keys(projectsByGuid)
            .map((projectGuid) => {
              return <Table.Row key={projectGuid}>
                <Table.Cell>
                  <b>{projectsByGuid[projectGuid].name}</b><br />
                  <CaseReviewLink projectGuid={projectGuid} />
                </Table.Cell>
                <Table.Cell> {JSON.stringify(projectsByGuid[projectGuid], null, 2)} </Table.Cell>
              </Table.Row>
            })
        }
        <Table.Row style={{ backgroundColor: '#F3F3F3' }} >
          <Table.Cell>
            <Grid stackable>
              <Grid.Column width={16}>
                <div style={{ float: 'right' }}>
                  <Button basic size="small" id="create-project-button" style={{ padding: '5px', width: '100px' }}>
                    Create New Project
                  </Button>
                </div>
              </Grid.Column>
            </Grid>
          </Table.Cell>
        </Table.Row>
      </Table.Body>
    </Table>
  }
}

export default ProjectsTable

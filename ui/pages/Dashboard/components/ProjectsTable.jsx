import React from 'react'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import ProjectsTableHeader from './ProjectsTableHeader'
import ProjectsTableRow from './ProjectsTableRow'

import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_DATE_CREATED,
} from '../constants'


class ProjectsTable extends React.Component {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    projectsByGuid: React.PropTypes.object.isRequired,
    projectsTable: React.PropTypes.object.isRequired,
  }

  render() {
    const {
      user,
      projectsByGuid,
      projectsTable,
    } = this.props

    return <Table celled striped style={{ width: '100%' }}>
      <Table.Body>

        <ProjectsTableHeader />

        {
          (() => {
            const keys = Object.keys(projectsByGuid)
            if (keys.length === 0) {
              return <Table.Row>
                <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
              </Table.Row>
            }

            let sortKey = null
            switch (projectsTable.sortOrder) {
              case SORT_BY_PROJECT_NAME: sortKey = guid => projectsByGuid[guid].name; break
              case SORT_BY_NUM_FAMILIES: sortKey = guid => projectsByGuid[guid].numFamilies; break
              case SORT_BY_NUM_INDIVIDUALS: sortKey = guid => projectsByGuid[guid].numIndividuals; break
              case SORT_BY_DATE_CREATED: sortKey = guid => projectsByGuid[guid].createdDate; break
              default:
                console.error(`Unexpected projectsSortOrder value: ${projectsTable.sortOrder}`)
                sortKey = p => p.guid
            }

            const sortedKeys = orderBy(keys, [sortKey], [projectsTable.sortDirection === 1 ? 'asc' : 'desc'])
            return sortedKeys.map((projectGuid) => {
              return <ProjectsTableRow
                key={projectGuid}
                user={user}
                project={projectsByGuid[projectGuid]}
              />
            })
          })()
        }
      </Table.Body>
    </Table>
  }
}

const mapStateToProps = ({
  user,
  projectsByGuid,
  projectsTable,
}) => ({
  user,
  projectsByGuid,
  projectsTable,
})

export default connect(mapStateToProps)(ProjectsTable)

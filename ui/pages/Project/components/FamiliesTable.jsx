import React from 'react'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'
import ProjectsTableHeader from './ProjectsTableHeader'
import ProjectsTableRow from './ProjectsTableRow'
import FilterSelector from './FilterSelector'
import { HorizontalSpacer } from '../../../shared/components/Spacers'

import {
  //SORT_BY_FAMILY_NAME,
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

    return <div>
      <div style={{ marginLeft: '10px' }}>
        <span style={{ fontSize: '12pt', fontWeight: '600' }}>
          Projects:
        </span>
        <HorizontalSpacer width={50} />
        <FilterSelector />
      </div>
      <Table striped stackable style={{ width: '100%' }}>
        <ProjectsTableHeader />
        <Table.Body>
          {
            (() => {
              const keys = Object.keys(projectsByGuid)

              if (keys.length === 0) {
                const tableIsEmpty = <Table.Row>
                  <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
                </Table.Row>
                return tableIsEmpty
              }

              let sortKey = null
              switch (projectsTable.sortColumn) {
                case SORT_BY_PROJECT_NAME: sortKey = guid => projectsByGuid[guid].name; break
                case SORT_BY_NUM_FAMILIES: sortKey = guid => projectsByGuid[guid].numFamilies; break
                case SORT_BY_NUM_INDIVIDUALS: sortKey = guid => projectsByGuid[guid].numIndividuals; break
                case SORT_BY_PROJECT_SAMPLES: sortKey = guid => (
                  projectsByGuid[guid].datasets && projectsByGuid[guid].datasets.map(
                    d => `${d.sequencingType}:${d.numSamples / 10000.0}`,  // sort by data type, then number of samples
                  ).join(',')) || 'Z'
                  break
                case SORT_BY_DATE_CREATED: sortKey = guid => projectsByGuid[guid].createdDate; break
                default:
                  console.error(`Unexpected projectsTable.SortColumn value: ${projectsTable.sortColumn}`)
                  sortKey = p => p.guid
              }

              let sortDirection = projectsTable.sortDirection
              if (projectsTable.sortColumn === SORT_BY_DATE_CREATED) {
                sortDirection *= -1
              }
              const sortedKeys = orderBy(keys, [sortKey], [sortDirection === 1 ? 'asc' : 'desc'])
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
    </div>
  }
}

const mapStateToProps = ({ user, projectsByGuid, projectsTable }) => ({ user, projectsByGuid, projectsTable })

export default connect(mapStateToProps)(ProjectsTable)

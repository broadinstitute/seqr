import React from 'react'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'
import ProjectsTableHeader from './ProjectsTableHeader'
import ProjectsTableRow from './ProjectsTableRow'
import FilterSelector from './FilterSelector'
import { HorizontalSpacer } from '../../../shared/components/Spacers'

import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_DATE_CREATED,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_PROJECT_SAMPLES,
  SORT_BY_ANALYSIS,
} from '../constants'

const TABLE_IS_EMPTY_ROW = <Table.Row>
  <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
</Table.Row>

const computeSortedProjectGuids = (projectsByGuid, sortColumn, sortDirection) => {
  const projectGuids = Object.keys(projectsByGuid)

  if (projectGuids.length === 0) {
    return projectGuids
  }

  let sortKey = null
  switch (sortColumn) {
    case SORT_BY_PROJECT_NAME: sortKey = guid => projectsByGuid[guid].name; break
    case SORT_BY_DATE_CREATED: sortKey = guid => projectsByGuid[guid].createdDate; break
    case SORT_BY_NUM_FAMILIES: sortKey = guid => projectsByGuid[guid].numFamilies; break
    case SORT_BY_NUM_INDIVIDUALS: sortKey = guid => projectsByGuid[guid].numIndividuals; break
    case SORT_BY_PROJECT_SAMPLES: sortKey = guid => (
      projectsByGuid[guid].datasets && projectsByGuid[guid].datasets.map(
        d => `${d.sequencingType}:${d.numSamples / 10000.0}`,  // sort by data type, then number of samples
      ).join(',')) || 'Z'
      break
    case SORT_BY_ANALYSIS: sortKey = (guid) => {
      // sort by % families solved, num families solved, num variant tags, num families <= in that order
      return projectsByGuid[guid].numFamilies &&
        (
          ((10e9 * projectsByGuid[guid].numFamiliesSolved) / projectsByGuid[guid].numFamilies) +
          ((10e5 * projectsByGuid[guid].numFamiliesSolved) || (10 * projectsByGuid[guid].numVariantTags) || (10e-3 * projectsByGuid[guid].numFamilies))
        )
    }; break
    default:
      console.error(`Unexpected projectsTable.SortColumn value: ${sortColumn}`)
      sortKey = p => p.guid
  }

  if (sortColumn === SORT_BY_DATE_CREATED) {
    sortDirection *= -1
  }
  const sortedProjectGuids = orderBy(projectGuids, [sortKey], [sortDirection === 1 ? 'asc' : 'desc'])

  return sortedProjectGuids
}


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
        <ProjectsTableHeader user={user} />
        <Table.Body>
          {
            (() => {
              const sortedProjectGuids = computeSortedProjectGuids(projectsByGuid, projectsTable.sortColumn, projectsTable.sortDirection)

              if (sortedProjectGuids.length > 0) {
                return sortedProjectGuids.map((projectGuid) => {
                  return <ProjectsTableRow
                    key={projectGuid}
                    user={user}
                    project={projectsByGuid[projectGuid]}
                  />
                })
              }

              return TABLE_IS_EMPTY_ROW
            })()
          }
        </Table.Body>
      </Table>
    </div>
  }
}

const mapStateToProps = ({ user, projectsByGuid, projectsTable }) => ({ user, projectsByGuid, projectsTable })

export default connect(mapStateToProps)(ProjectsTable)

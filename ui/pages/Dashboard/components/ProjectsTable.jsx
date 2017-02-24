import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Icon, Table } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'
import ProjectsTableHeader from './ProjectsTableHeader'
import ProjectsTableRow from './ProjectsTableRow'
import FilterSelector from './FilterSelector'
import { showModal } from '../reducers/rootReducer'
import { HorizontalSpacer } from '../../../shared/components/Spacers'


import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_DATE_CREATED,
  SORT_BY_DATE_LAST_ACCESSED,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_PROJECT_SAMPLES,
  SORT_BY_TAGS,
  SORT_BY_ANALYSIS,

  SHOW_ALL,

  ADD_PROJECT_MODAL,
} from '../constants'

const TABLE_IS_EMPTY_ROW = <Table.Row>
  <Table.Cell />
  <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
</Table.Row>

const computeSortedProjectGuids = (projectGuids, projectsByGuid, datasetsByGuid, sortColumn, sortDirection) => {
  if (projectGuids.length === 0) {
    return projectGuids
  }

  let sortKey = null
  switch (sortColumn) {
    case SORT_BY_PROJECT_NAME: sortKey = guid => projectsByGuid[guid].name; break
    case SORT_BY_DATE_CREATED: sortKey = guid => projectsByGuid[guid].createdDate; break
    case SORT_BY_DATE_LAST_ACCESSED: sortKey = guid => projectsByGuid[guid].deprecatedLastAccessedDate; break
    case SORT_BY_NUM_FAMILIES: sortKey = guid => projectsByGuid[guid].numFamilies; break
    case SORT_BY_NUM_INDIVIDUALS: sortKey = guid => projectsByGuid[guid].numIndividuals; break
    case SORT_BY_PROJECT_SAMPLES: sortKey = guid => (projectsByGuid[guid].datasetGuids &&
      projectsByGuid[guid].datasetGuids.map(
        d => `${datasetsByGuid[d].sequencingType}:${datasetsByGuid[d].numSamples / 10000.0}`,  // sort by data type, then number of samples
      ).join(',')) || 'A'
      break
    case SORT_BY_TAGS: sortKey = guid => projectsByGuid[guid].numVariantTags; break
    case SORT_BY_ANALYSIS: sortKey = (guid) => {
      // sort by % families solved, num families solved, num variant tags, num families <= in that order
      return projectsByGuid[guid].numFamilies &&
        (
          ((10e9 * projectsByGuid[guid].analysisStatusCounts.Solved || 0) / projectsByGuid[guid].numFamilies) +
          ((10e5 * projectsByGuid[guid].analysisStatusCounts.Solved || 0) || (10e-3 * projectsByGuid[guid].numFamilies))
        )
    }; break
    default:
      console.error(`Unexpected projectsTableState.SortColumn value: ${sortColumn}`)
      sortKey = p => p.guid
  }

  if (sortColumn === SORT_BY_DATE_CREATED || sortColumn === SORT_BY_DATE_LAST_ACCESSED) {
    sortDirection *= -1
  }
  const sortedProjectGuids = orderBy(projectGuids, [sortKey], [sortDirection === 1 ? 'asc' : 'desc'])

  return sortedProjectGuids
}


class ProjectsTable extends React.Component {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    projectsByGuid: React.PropTypes.object.isRequired,
    projectCategoriesByGuid: React.PropTypes.object.isRequired,
    datasetsByGuid: React.PropTypes.object.isRequired,
    projectsTableState: React.PropTypes.object.isRequired,
    showModal: React.PropTypes.func.isRequired,
  }

  render() {
    const {
      user,
      projectsByGuid,
      projectCategoriesByGuid,
      datasetsByGuid,
      projectsTableState,
    } = this.props

    return <div>
      <div style={{ marginLeft: '10px' }}>
        <span style={{ fontSize: '12pt', fontWeight: '600' }}>
          Projects:
        </span>
        <HorizontalSpacer width={30} />
        <FilterSelector />
      </div>
      <Table striped stackable style={{ width: '100%' }}>
        <ProjectsTableHeader user={user} />
        <Table.Body>
          {
            (() => {
              const filteredProjectGuids = Object.keys(projectsByGuid).filter((projectGuid) => {
                if (projectsTableState.filter === SHOW_ALL) {
                  return true
                }
                return projectsByGuid[projectGuid].projectCategoryGuids.indexOf(projectsTableState.filter) > -1
              })

              const sortedProjectGuids = computeSortedProjectGuids(filteredProjectGuids, projectsByGuid, datasetsByGuid, projectsTableState.sortColumn, projectsTableState.sortDirection)
              if (sortedProjectGuids.length > 0) {
                return sortedProjectGuids.map((projectGuid) => {
                  return <ProjectsTableRow
                    key={projectGuid}
                    user={user}
                    project={projectsByGuid[projectGuid]}
                    projectCategoriesByGuid={projectCategoriesByGuid}
                    datasetsByGuid={datasetsByGuid}
                  />
                })
              }

              return TABLE_IS_EMPTY_ROW
            })()
          }
          {
            this.props.user.is_staff &&
              <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
                <Table.Cell colSpan={8} />
                <Table.Cell colSpan={10}>
                  <a href="#." onClick={() => this.props.showModal(ADD_PROJECT_MODAL)}>
                    <Icon name="plus" />Create Project
                  </a>
                </Table.Cell>
              </Table.Row>
          }
        </Table.Body>
      </Table>
    </div>
  }
}

const mapStateToProps = ({
  user,
  projectsByGuid,
  projectCategoriesByGuid,
  datasetsByGuid,
  projectsTableState,
}) => ({
  user,
  projectsByGuid,
  projectCategoriesByGuid,
  datasetsByGuid,
  projectsTableState,
})


const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ProjectsTable)

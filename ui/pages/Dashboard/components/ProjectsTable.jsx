import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Table } from 'semantic-ui-react'

import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/ExportTableButton'

import FilterSelector from './table-header/FilterSelector'
import ProjectTableHeader from './table-header/ProjectTableHeader'
import ProjectTableRow from './table-body/ProjectTableRow'
import ProjectTableFooter from './table-footer/ProjectTableFooter'

import { getUser, showModal } from '../reducers/rootReducer'
import { getVisibleProjectsInSortedOrder } from '../utils/visibleProjectsSelector'

const TABLE_IS_EMPTY_ROW = <Table.Row>
  <Table.Cell />
  <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
</Table.Row>


class ProjectsTable extends React.Component
{
  static propTypes = {
    visibleProjects: React.PropTypes.array.isRequired,
  }

  render() {
    const {
      visibleProjects,
    } = this.props

    return <div>
      <div style={{ marginLeft: '10px' }}>
        <span style={{ fontSize: '12pt', fontWeight: '600' }}>
          Projects:
        </span>
        <HorizontalSpacer width={30} />
        <FilterSelector />

        <div style={{ float: 'right', padding: '0px 45px 10px 0px' }}>
          <ExportTableButton urls={[{ name: 'Projects Table', url: '/api/dashboard/export_projects_table' }]} />
        </div>
      </div>
      <Table striped stackable style={{ width: '100%' }}>
        <ProjectTableHeader />
        <Table.Body>
          {
            visibleProjects.length > 0 ?
              visibleProjects.map(project => (
                <ProjectTableRow key={project.projectGuid} project={project} />
              ))
              : TABLE_IS_EMPTY_ROW
          }
          <ProjectTableFooter />
        </Table.Body>
      </Table>
    </div>
  }
}

export { ProjectsTable as ProjectsTableComponent }

const mapStateToProps = state => ({
  user: getUser(state),
  visibleProjects: getVisibleProjectsInSortedOrder(state),
})


const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ProjectsTable)

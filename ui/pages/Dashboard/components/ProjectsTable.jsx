import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'

import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'

import FilterSelector from './table-header/FilterSelector'
import ProjectTableHeader from './table-header/ProjectTableHeader'
import ProjectTableRow from './table-body/ProjectTableRow'
import ProjectTableFooter from './table-footer/ProjectTableFooter'

import { projectsLoading, fetchProjects } from '../../../redux/rootReducer'
import { getVisibleProjectsInSortedOrder } from '../utils/visibleProjectsSelector'

// TODO spinner
const TABLE_LOADING_ROW = (
  <Table.Row>
    <Table.Cell />
    <Table.Cell style={{ padding: '10px' }}>Loading...</Table.Cell>
  </Table.Row>)

const TABLE_IS_EMPTY_ROW = (
  <Table.Row>
    <Table.Cell />
    <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
  </Table.Row>)

class ProjectsTable extends React.Component
{
  static propTypes = {
    visibleProjects: PropTypes.array.isRequired,
    loading: PropTypes.bool.isRequired,
    fetchProjects: PropTypes.func.isRequired,
  }

  // TODO download should be done via redux, not with hardcoded url

  render() {
    let tableContent
    if (this.props.loading) {
      tableContent = TABLE_LOADING_ROW
    } else if (this.props.visibleProjects.length > 0) {
      tableContent = this.props.visibleProjects.map(project => (
        <ProjectTableRow key={project.projectGuid} project={project} />
      ))
    } else {
      tableContent = TABLE_IS_EMPTY_ROW
    }

    return (
      <div>
        <div style={{ marginLeft: '10px' }}>
          <span style={{ fontSize: '12pt', fontWeight: '600' }}>
            Projects:
          </span>
          <HorizontalSpacer width={30} />
          <FilterSelector />
          <div style={{ paddingLeft: '50px', display: 'inline-block', textAlign: 'center', fontSize: '16px', fontWeight: 400, fontStyle: 'italic' }}>
             Welcome to the new seqr dashboard. The previous version can be found <a href="/projects">here</a>.
          </div>
          <div style={{ float: 'right', padding: '0px 45px 10px 0px' }}>
            <ExportTableButton urls={[{ name: 'Projects', url: '/api/dashboard/export_projects_table' }]} />
          </div>
        </div>
        <Table striped stackable style={{ width: '100%' }}>
          <ProjectTableHeader />
          <Table.Body>
            {tableContent}
            <ProjectTableFooter />
          </Table.Body>
        </Table>
      </div>)
  }

  componentDidMount() {
    this.props.fetchProjects()
  }
}

export { ProjectsTable as ProjectsTableComponent }

const mapStateToProps = state => ({
  visibleProjects: getVisibleProjectsInSortedOrder(state),
  loading: projectsLoading(state),
})


const mapDispatchToProps = {
  fetchProjects,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectsTable)

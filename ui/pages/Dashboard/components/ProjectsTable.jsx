import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { connect } from 'react-redux'
import { Table, Header } from 'semantic-ui-react'

import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import TableLoading from 'shared/components/table/TableLoading'

import FilterSelector from './table-header/FilterSelector'
import ProjectTableHeader from './table-header/ProjectTableHeader'
import ProjectTableRow from './table-body/ProjectTableRow'
import ProjectTableFooter from './table-footer/ProjectTableFooter'

import { fetchProjects } from '../../../redux/rootReducer'
import { getProjectsIsLoading } from '../../../redux/selectors'
import { getVisibleProjectsInSortedOrder } from '../utils/visibleProjectsSelector'


const InlineHeader = styled(Header)`
  display: inline-block;
  margin: 0 !important;
`

const RightAligned = styled.span`
  float: right;
`

const PROJECT_EXPORT_URLS = [{ name: 'Projects', url: '/api/dashboard/export_projects_table' }]

const TABLE_IS_EMPTY_ROW = (
  <Table.Row>
    <Table.Cell />
    <Table.Cell>0 projects found</Table.Cell>
  </Table.Row>)

class ProjectsTable extends React.Component
{
  static propTypes = {
    visibleProjects: PropTypes.array.isRequired,
    loading: PropTypes.bool.isRequired,
    fetchProjects: PropTypes.func.isRequired,
  }

  render() {
    let tableContent
    if (this.props.loading) {
      tableContent = <TableLoading />
    } else if (this.props.visibleProjects.length > 0) {
      tableContent = this.props.visibleProjects.map(project => (
        <ProjectTableRow key={project.projectGuid} project={project} />
      ))
    } else {
      tableContent = TABLE_IS_EMPTY_ROW
    }

    return (
      <div>
        <HorizontalSpacer width={10} />
        <InlineHeader size="medium" content="Projects:" />
        <HorizontalSpacer width={30} />
        <FilterSelector />
        <RightAligned>
          <ExportTableButton downloads={PROJECT_EXPORT_URLS} />
          <HorizontalSpacer width={45} />
        </RightAligned>
        <Table striped stackable>
          <ProjectTableHeader />
          <Table.Body>
            {tableContent}
          </Table.Body>
          <ProjectTableFooter />
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
  loading: getProjectsIsLoading(state),
})


const mapDispatchToProps = {
  fetchProjects,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectsTable)

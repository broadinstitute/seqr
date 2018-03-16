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

import { getUser, showModal } from '../../../redux/rootReducer'
import { getVisibleProjectsInSortedOrder } from '../utils/visibleProjectsSelector'

const TABLE_IS_EMPTY_ROW = (
  <Table.Row>
    <Table.Cell />
    <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
  </Table.Row>)

class ProjectsTable extends React.Component
{
  static propTypes = {
    visibleProjects: PropTypes.array.isRequired,
  }

  render() {

    const {
      visibleProjects,
    } = this.props

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
      </div>)
  }
}

export { ProjectsTable as ProjectsTableComponent }

const mapStateToProps = state => ({
  user: getUser(state),
  visibleProjects: getVisibleProjectsInSortedOrder(state),
})


const mapDispatchToProps = {
  showModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectsTable)

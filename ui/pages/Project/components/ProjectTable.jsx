import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Table, Form } from 'semantic-ui-react'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'

import ProjectOverview from './ProjectOverview'
import TableBody from './table-body/TableBody'
import { getProject } from '../reducers/rootReducer'

const ProjectTable = props => <Form>
  <ProjectOverview />
  <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
    <ExportTableButton urls={[
      { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_project_families` },
      { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_project_individuals?include_phenotypes=1` }]}
    />
  </div>
  <Table celled style={{ width: '100%' }}>
    <TableBody />
  </Table>
</Form>

export { ProjectTable as ProjectTableComponent }

ProjectTable.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(ProjectTable)

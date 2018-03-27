import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Table } from 'semantic-ui-react'
import DocumentTitle from 'react-document-title'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import { getProject } from 'redux/rootReducer'
import ProjectOverview from './ProjectOverview'

import TableBody from './table-body/TableBody'


const ProjectPageUI = props =>
  <Form>
    <DocumentTitle title={`seqr: ${props.project.name}`} />
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

ProjectPageUI.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(ProjectPageUI)


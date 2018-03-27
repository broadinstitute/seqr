import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Header, Form, Table } from 'semantic-ui-react'
import DocumentTitle from 'react-document-title'

import { projectsLoading, loadProject, getProject } from 'redux/rootReducer'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ProjectOverview from './components/ProjectOverview'
import FamilyTableBody from './components/table-body/TableBody'


class Project extends React.Component
{
  static propTypes = {
    project: PropTypes.object,
    match: PropTypes.object,
    loading: PropTypes.bool.isRequired,
    loadProject: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    props.loadProject(props.match.params.projectGuid)
  }

  render() {
    if (this.props.project) {
      return (
        <Form>
          <DocumentTitle title={`seqr: ${this.props.project.name}`} />
          <ProjectOverview />
          <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
            <ExportTableButton urls={[
              { name: 'Families', url: `/api/project/${this.props.project.projectGuid}/export_project_families` },
              { name: 'Individuals', url: `/api/project/${this.props.project.projectGuid}/export_project_individuals?include_phenotypes=1` }]}
            />
          </div>
          <Table celled style={{ width: '100%' }}>
            <FamilyTableBody />
          </Table>
        </Form>
      )
    } else if (this.props.loading) {
      return <Loader inline="centered" active />
    }
    // TODO shared 404 component
    return <Header size="huge" textAlign="center">Error 404: Page Not Found</Header>
  }
}

const mapDispatchToProps = {
  loadProject,
}

const mapStateToProps = state => ({
  project: getProject(state),
  loading: projectsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(Project)

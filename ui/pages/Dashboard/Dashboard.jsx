import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import { Divider } from 'semantic-ui-react'

import { fetchProjects } from 'redux/rootReducer'
import ProjectsTable from './components/ProjectsTable'


class Dashboard extends React.PureComponent {
  static propTypes = {
    fetchProjects: PropTypes.func.isRequired,
  }

  componentDidMount() {
    this.props.fetchProjects()
  }

  render() {
    return (
      <div>
        <DocumentTitle title="seqr: home" />
        <div style={{ textAlign: 'center', fontSize: '16px', fontWeight: 400, fontStyle: 'italic' }}>
           Welcome to the new seqr dashboard. The deprecated previous version can be found <a href="/projects">here</a>.
        </div>
        <Divider />
        <ProjectsTable />
      </div>
    )
  }
}

const mapDispatchToProps = {
  fetchProjects,
}

export default connect(null, mapDispatchToProps)(Dashboard)

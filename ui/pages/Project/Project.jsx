import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Loader, Header } from 'semantic-ui-react'

import { projectsLoading, fetchProject, getProject } from 'redux/rootReducer'
import ProjectPageUI from './components/ProjectPageUI'


class Project extends React.Component
{
  static propTypes = {
    project: PropTypes.object,
    loading: PropTypes.bool.isRequired,
    fetchProject: PropTypes.func.isRequired,
  }

  render() {
    if (this.props.project) {
      return <ProjectPageUI />
    } else if (this.props.loading) {
      return <Loader inline="centered" active />
    }
    // TODO shared 404 component
    return <Header size="huge" textAlign="center">Error 404: Page Not Found</Header>
  }

  componentDidMount() {
    this.props.fetchProject()
  }
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  fetchProject: () => dispatch(fetchProject(ownProps.match.params.projectGuid)),
})

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state, ownProps),
  loading: projectsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(Project)

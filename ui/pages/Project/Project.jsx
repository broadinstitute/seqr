import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'
import { Loader, Header } from 'semantic-ui-react'

import { getCurrentProject } from 'redux/selectors'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'
import { loadProject, unloadProject } from './reducers'
import { getProjectDetailsIsLoading } from './selectors'
import ProjectPageUI from './components/ProjectPageUI'
import CaseReview from './components/CaseReview'
import FamilyPage from './components/FamilyPage'
import Matchmaker from './components/Matchmaker'


// TODO shared 404 component
const Error404 = () => (<Header size="huge" textAlign="center">Error 404: Page Not Found</Header>)


class Project extends React.Component
{
  static propTypes = {
    project: PropTypes.object,
    match: PropTypes.object,
    loading: PropTypes.bool.isRequired,
    loadProject: PropTypes.func.isRequired,
    unloadProject: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    props.loadProject(props.match.params.projectGuid)
  }

  componentWillUnmount() {
    this.props.unloadProject()
  }

  render() {
    if (this.props.project && this.props.project.detailsLoaded) {
      return (
        <Switch>
          <Route path={`${this.props.match.url}/project_page`} component={ProjectPageUI} />
          <Route path={`${this.props.match.url}/case_review`} component={CaseReview} />
          <Route path={`${this.props.match.url}/analysis_group/:analysisGroupGuid`} component={ProjectPageUI} />
          <Route path={`${this.props.match.url}/family_page/:familyGuid/matchmaker_exchange`} component={Matchmaker} />
          <Route path={`${this.props.match.url}/family_page/:familyGuid`} component={FamilyPage} />
          <Route path={`${this.props.match.url}/saved_variants`} component={SavedVariants} />
          <Route component={() => <Error404 />} />
        </Switch>
      )
    } else if (this.props.loading) {
      return <Loader inline="centered" active />
    }
    return <Error404 />
  }
}

const mapDispatchToProps = {
  loadProject, unloadProject,
}

const mapStateToProps = state => ({
  project: getCurrentProject(state),
  loading: getProjectDetailsIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(Project)

import React from 'react'
import ReactDOM from 'react-dom'
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import { connect, Provider } from 'react-redux'
import PropTypes from 'prop-types'
import { Loader } from 'semantic-ui-react'

import BaseLayout from 'shared/components/page/BaseLayout'
import Dashboard from 'pages/Dashboard/Dashboard'
import Project from 'pages/Project/Project'
import LoadWorkspaceData, { WorkspaceAccessError } from 'pages/AnvilWorkspace/LoadWorkspaceData'
import VariantSearch from 'pages/Search/VariantSearch'
import DataManagement from 'pages/DataManagement/DataManagement'
import Report from 'pages/Report/Report'
import SummaryData from 'pages/SummaryData/SummaryData'
import Login from 'pages/Login/Login'
import AcceptPolicies from 'pages/Login/components/AcceptPolicies'
import PUBLIC_ROUTES from 'pages/Public/PublicRoutes'
import LandingPage from 'pages/Public/components/LandingPage'
import rootReducer from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import configureStore from 'redux/utils/configureStore'
import { Error404 } from 'shared/components/page/Errors'

import 'semantic-ui-css/semantic.min.css'
import 'shared/global.css'

const BaseHome = ({ user, ...props }) => (
  user && Object.keys(user).length ? <Dashboard {...props} /> : <LandingPage />
)

BaseHome.propTypes = {
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

const Home = connect(mapStateToProps)(BaseHome)

ReactDOM.render(
  <Provider store={configureStore(rootReducer, window.initialJSON)}>
    <BrowserRouter>
      <BaseLayout>
        <Switch>
          <Route exact path="/" component={Home} />
          <Route path="/dashboard" component={Dashboard} />
          <Route path="/project/:projectGuid" component={Project} />
          <Route path="/create_project_from_workspace/:namespace/:name" component={LoadWorkspaceData} />
          <Route path="/workspace/:namespace/:name" component={WorkspaceAccessError} />
          <Route path="/variant_search" component={VariantSearch} />
          <Route path="/data_management" component={DataManagement} />
          <Route path="/report" component={Report} />
          <Route path="/summary_data" component={SummaryData} />
          <Route path="/login" component={Login} />
          <Route path="/accept_policies" component={AcceptPolicies} />
          <React.Suspense fallback={<Loader />}>
            {PUBLIC_ROUTES.map(props => <Route {...props} />)}
          </React.Suspense>
          <Route component={Error404} />
        </Switch>
      </BaseLayout>
    </BrowserRouter>
  </Provider>,
  document.getElementById('reactjs-root'),
)

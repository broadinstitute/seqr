import 'react-hot-loader/patch'
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import { connect, Provider } from 'react-redux'
import PropTypes from 'prop-types'

import BaseLayout from 'shared/components/page/BaseLayout'
import Dashboard from 'pages/Dashboard/Dashboard'
import Project from 'pages/Project/Project'
import LoadWorkspaceData, { WorkspaceAccessError } from 'pages/AnvilWorkspace/LoadWorkspaceData'
import VariantSearch from 'pages/Search/VariantSearch'
import DataManagement from 'pages/DataManagement/DataManagement'
import Report from 'pages/Report/Report'
import SummaryData from 'pages/SummaryData/SummaryData'
import Login from 'pages/Login/components/Login'
import ForgotPassword from 'pages/Login/components/ForgotPassword'
import SetPassword from 'pages/Login/components/SetPassword'
import AcceptPolicies from 'pages/Login/components/AcceptPolicies'
import LandingPage from 'pages/Public/LandingPage'
import MatchmakerDisclaimer from 'pages/Public/MatchmakerDisclaimer'
import MatchmakerInfo from 'pages/Public/MatchmakerInfo'
import PrivacyPolicy from 'pages/Public/PrivacyPolicy'
import TermsOfService from 'pages/Public/TermsOfService'
import rootReducer from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import { configureStore } from 'redux/utils/configureStore'

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
    <AppContainer>
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
            <Route path="/users/forgot_password" component={ForgotPassword} />
            <Route path="/users/set_password/:userToken" component={SetPassword} />
            <Route path="/matchmaker/matchbox" component={MatchmakerInfo} />
            <Route path="/matchmaker/disclaimer" component={MatchmakerDisclaimer} />
            <Route path="/privacy_policy" component={PrivacyPolicy} />
            <Route path="/terms_of_service" component={TermsOfService} />
            <Route path="/accept_policies" component={AcceptPolicies} />
            <Route component={() => <div>Invalid URL</div>} />
          </Switch>
        </BaseLayout>
      </BrowserRouter>
    </AppContainer>
  </Provider>,
  document.getElementById('reactjs-root'),
)

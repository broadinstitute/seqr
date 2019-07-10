import 'react-hot-loader/patch'
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import { connect, Provider } from 'react-redux'
import PropTypes from 'prop-types'

import BaseLayout from 'shared/components/page/BaseLayout'
import GeneDetail from 'shared/components/panel/genes/GeneDetail'
import Dashboard from 'pages/Dashboard/Dashboard'
import Project from 'pages/Project/Project'
import VariantSearch from 'pages/Search/VariantSearch'
import GeneInfoSearch from 'pages/GeneInfoSearch'
import LocusLists from 'pages/LocusLists'
import Staff from 'pages/Staff/Staff'
import Login from 'pages/Login/components/Login'
import ForgotPassword from 'pages/Login/components/ForgotPassword'
import SetPassword from 'pages/Login/components/SetPassword'
import LandingPage from 'pages/Public/LandingPage'
import MatchmakerDisclaimer from 'pages/Public/MatchmakerDisclaimer'
import MatchmakerInfo from 'pages/Public/MatchmakerInfo'
import rootReducer from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import { configureStore } from 'redux/utils/configureStore'

import 'semantic-ui-css/semantic-custom.css'
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
            <Route path="/variant_search" component={VariantSearch} />
            <Route path="/gene_info/:geneId" component={({ match }) => <GeneDetail geneId={match.params.geneId} />} />
            <Route path="/gene_info" component={GeneInfoSearch} />
            <Route path="/gene_lists" component={LocusLists} />
            <Route path="/staff" component={Staff} />
            <Route path="/login" component={Login} />
            <Route path="/users/forgot_password" component={ForgotPassword} />
            <Route path="/users/set_password" component={SetPassword} />
            <Route path="/matchmaker/matchbox" component={MatchmakerInfo} />
            <Route path="/matchmaker/disclaimer" component={MatchmakerDisclaimer} />
            <Route component={() => <div>Invalid URL</div>} />
          </Switch>
        </BaseLayout>
      </BrowserRouter>
    </AppContainer>
  </Provider>,
  document.getElementById('reactjs-root'),
)

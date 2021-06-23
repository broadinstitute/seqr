import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'

import { Error404 } from 'shared/components/page/Errors'
import Login from './components/Login'
import LoginError from './components/LoginError'

const LoginPage = ({ match }) => (
  <Switch>
    <Route path={`${match.url}/error/:error`} component={LoginError} />
    <Route path={match.url} component={Login} />
    <Route component={() => <Error404 />} />
  </Switch>
)

LoginPage.propTypes = {
  match: PropTypes.object,
}

export default LoginPage

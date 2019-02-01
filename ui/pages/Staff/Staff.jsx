import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'
import { Header } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import Anvil from './components/Anvil'

// TODO shared 404 component
const Error404 = () => (<Header size="huge" textAlign="center">Error 404: Page Not Found</Header>)
const Error401 = () => (<Header size="huge" textAlign="center">Error 401: Unauthorized</Header>)


const Staff = ({ match, user }) => (
  user.is_staff ? (
    <Switch>
      <Route path={`${match.url}/anvil`} component={Anvil} />
      <Route path={`${match.url}/anvil/projects/:allProjects`} component={Anvil} />
      <Route path={`${match.url}/anvil/:projectGuid`} component={Anvil} />
      <Route component={() => <Error404 />} />
    </Switch>
  ) : <Error401 />
)

Staff.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(Staff)

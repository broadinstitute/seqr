import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Divider, Message } from 'semantic-ui-react'

import { getGoogleLoginEnabled } from 'redux/selectors'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { login } from '../reducers'
import UserFormLayout from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
  { name: 'password', label: 'Password', type: 'password', validate: validators.required },
]

const Login = ({ onSubmit, googleLoginEnabled, location }) =>
  <UserFormLayout
    header="Login to seqr"
    onSubmit={onSubmit}
    form="login"
    fields={FIELDS}
    submitButtonText="Log In"
  >
    <Link to="/users/forgot_password">Forgot Password?</Link>
    {googleLoginEnabled &&
    <div>
      <Divider />
      {location.search === '?googleLoginFailed=true' &&
      <Message visible warning>
        Logging in has failed. Make sure you have registered your account on AnVIL. <br />
        Click this link <a href="https://anvil.terra.bio">https://anvil.terra.bio</a>, sign in to AnVIL with Google, and register your account.
      </Message> }
      <a href="/login/google-oauth2">Sign in with Google</a>
    </div>}

  </UserFormLayout>

Login.propTypes = {
  onSubmit: PropTypes.func,
  googleLoginEnabled: PropTypes.bool,
  location: PropTypes.object,
}

const mapDispatchToProps = {
  onSubmit: login,
}

const mapStateToProps = state => ({
  googleLoginEnabled: getGoogleLoginEnabled(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(Login)

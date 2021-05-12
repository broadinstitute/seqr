import React from 'react'
import PropTypes from 'prop-types'
import queryString from 'query-string'
import { connect } from 'react-redux'
import { Divider, Message, Button, Icon } from 'semantic-ui-react'

import { getGoogleLoginEnabled } from 'redux/selectors'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { ANVIL_URL } from 'shared/utils/constants'
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
    content={googleLoginEnabled &&
      <div>
        <br />
        <Button as="a" href={`/login/google-oauth2${location.search}`} primary>
          <Icon name="google" />
          Sign in with Google
        </Button>
        {queryString.parse(location.search).anvilLoginFailed &&
        <Message visible error>
          Unable to authorize the selected Google user. Please register your account in AnVIL by signing in and
          registering at <a href={ANVIL_URL} target="_blank">anvil.terra.bio</a>
        </Message> }
        {queryString.parse(location.search).googleLoginFailed &&
        <Message visible error>
          No seqr account found for the selected Google user
        </Message> }
        <Divider horizontal>Or</Divider>
      </div>
    }
    submitButtonText="Log In"
  />

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

import React from 'react'
import PropTypes from 'prop-types'
import queryString from 'query-string'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Divider, Message, Button, Icon, Accordion } from 'semantic-ui-react'

import { getGoogleLoginEnabled } from 'redux/selectors'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { ANVIL_URL } from 'shared/utils/constants'
import { login } from '../reducers'
import { UserFormContainer, UserForm } from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
  { name: 'password', label: 'Password', type: 'password', validate: validators.required },
]

const GOGGLE_SETUP_URL = 'https://support.terra.bio/hc/en-us/articles/360029186611-Setting-up-a-Google-account-with-a-non-Google-email'

const Login = ({ onSubmit, googleLoginEnabled, location }) => {
  const loginForm =
    <UserForm
      onSubmit={onSubmit}
      form="login"
      fields={FIELDS}
      submitButtonText="Log In"
    />

  const registerMessage =
    <span>
      Please register your account in AnVIL by signing in and registering
      at <a href={ANVIL_URL} target="_blank">anvil.terra.bio</a>
    </span>

  const loginPanels = [{
    title: { content: <span>Or, <a>sign in with Email/ Password</a></span>, icon: 'sign-in' },
    content: {
      content: (
        <div>
          <Message warning>
            Signing in to seqr with your email/ password will be deprecated. {registerMessage}, which will
            enable you to use the above &quot;Sign in with Google&quot; option. If the email associated with your
            account is not managed by google, follow <a href={GOGGLE_SETUP_URL} target="_blank">these instructions </a>
            to register the email with google before registering with AnVIL.
          </Message>
          {loginForm}
        </div>
      ),
    },
  }]

  return (
    <UserFormContainer header="Login to seqr">
      {googleLoginEnabled ?
        <div>
          <br />
          <Button as="a" href={`/login/google-oauth2${location.search}`} primary>
            <Icon name="google" />
            Sign in with Google
          </Button>
          <Message hidden={!queryString.parse(location.search).anvilLoginFailed} error>
            Unable to authorize the selected Google user. {registerMessage}
          </Message>
          <Message hidden={!queryString.parse(location.search).googleLoginFailed} error>
            No seqr account found for the selected Google user
          </Message>
          <Divider section />
          <Accordion panels={loginPanels} />
        </div> :
        <div>
          {loginForm}
          <Link to="/users/forgot_password">Forgot Password?</Link>
        </div>}
    </UserFormContainer>
  )
}


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

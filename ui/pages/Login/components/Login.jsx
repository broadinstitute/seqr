import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import GoogleButton from 'react-google-button'
import queryString from 'query-string'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { login, googleLogin } from '../reducers'
import UserFormLayout from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
  { name: 'password', label: 'Password', type: 'password', validate: validators.required },
]

export const OAuth2Callback = ({ location }) => {
  // Send the authentication results to the backend to finish the logging-in procedure
  new HttpRequestHelper('/api/login_oauth2callback',
    () => {
      window.close()
      // Redirect to next page or home page
      window.opener.location.href = `${window.opener.location.origin}${queryString.parse(window.opener.location.search).next || ''}`
    },
    (e) => {
      window.close()
      window.opener.focus()
      // throw new SubmissionError({ _error: [e.message] })
      // eslint-disable-next-line no-alert
      alert(e.message)
    },
  ).post(location.pathname + location.search)
  return <div>Logging in with Google ...</div>
}

OAuth2Callback.propTypes = {
  location: PropTypes.object.isRequired,
}

const Login = ({ onSubmit }) =>
  <UserFormLayout
    header="Login to seqr"
    onSubmit={onSubmit}
    form="login"
    fields={FIELDS}
    submitButtonText="Log In"
  >
    <Link to="/users/forgot_password">Forgot Password?</Link>
    <br />
    <GoogleButton onClick={googleLogin} />
  </UserFormLayout>

Login.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: login,
}

export default connect(null, mapDispatchToProps)(Login)

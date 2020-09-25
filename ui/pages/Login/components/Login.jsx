import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { SubmissionError } from 'redux-form'
import GoogleButton from 'react-google-button'
import queryString from 'query-string'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { login } from '../reducers'
import UserFormLayout from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
  { name: 'password', label: 'Password', type: 'password', validate: validators.required },
]

export const googleLogin = () => {
  return new HttpRequestHelper('/api/login_google',
    (responseJson) => {
      // Redirect to google auth website
      const width = 600
      const height = 800
      const left = (window.screen.width - width) / 2
      const top = (window.screen.height - height) / 2
      const params = `scrollbars=no,status=no,location=no,toolbar=no,menubar=no,
        width=${width},height=${height},left=${left},top=${top}`
      const win = window.open(responseJson.data, 'Google Sign In', params)
      win.focus()
    },
    (e) => {
      throw new SubmissionError({ _error: [e.message] })
    },
  ).get()
}

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

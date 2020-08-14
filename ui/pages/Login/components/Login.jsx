import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { SubmissionError } from 'redux-form'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { login } from '../reducers'
import UserFormLayout from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
  { name: 'password', label: 'Password', type: 'password', validate: validators.required },
]


const googleLogin = () => {
  return new HttpRequestHelper('/api/login_google',
    (responseJson) => {
      // Redirect to google auth website
      window.location.href = responseJson.data
    },
    (e) => {
      throw new SubmissionError({ _error: [e.message] })
    },
  ).get()
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
    <button onClick={googleLogin}>Logging in with Google</button>
  </UserFormLayout>

Login.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: login,
}

export default connect(null, mapDispatchToProps)(Login)

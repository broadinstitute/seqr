import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { login } from '../reducers'
import UserFormLayout from './UserFormLayout'

const FIELDS = [
  {
    name: 'email',
    label: 'Email',
    width: 16,
    inline: true,
  },
  {
    name: 'password',
    label: 'Password',
    type: 'password',
    width: 16,
    inline: true,
  },
]

const Login = ({ onSubmit }) =>
  <UserFormLayout
    header="Login to seqr"
    onSubmit={onSubmit}
    form="login"
    fields={FIELDS}
    submitButtonText="Log In"
  >
    <Link to="/users/forgot_password">Forgot Password?</Link>
  </UserFormLayout>

Login.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: login,
}

export default connect(null, mapDispatchToProps)(Login)

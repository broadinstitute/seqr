import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { validators } from 'shared/components/form/ReduxFormWrapper'
import { login } from '../reducers'
import { UserFormContainer, UserForm } from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
  { name: 'password', label: 'Password', type: 'password', validate: validators.required },
]

const Login = ({ onSubmit }) => (
  <UserFormContainer header="Login to seqr">
    <UserForm
      onSubmit={onSubmit}
      form="login"
      fields={FIELDS}
      submitButtonText="Log In"
    />
    <Link to="/login/forgot_password">Forgot Password?</Link>
  </UserFormContainer>
)

Login.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: login,
}

export default connect(null, mapDispatchToProps)(Login)

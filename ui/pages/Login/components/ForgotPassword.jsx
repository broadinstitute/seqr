import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { validators } from 'shared/components/form/ReduxFormWrapper'
import { forgotPassword } from '../reducers'
import UserFormLayout from './UserFormLayout'

const FIELDS = [
  { name: 'email', label: 'Email', validate: validators.required },
]

const ForgotPassword = ({ onSubmit }) =>
  <UserFormLayout
    header="Reset your Password"
    subheader="You will receive an email with a link to reset your password"
    onSubmit={onSubmit}
    successMessage="An email to reset your password has been sent. If you do not receive the email, please contact us."
    form="reset-password"
    fields={FIELDS}
  />

ForgotPassword.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: forgotPassword,
}

export default connect(null, mapDispatchToProps)(ForgotPassword)

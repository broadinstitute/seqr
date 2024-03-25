import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import queryString from 'query-string'

import { USER_NAME_FIELDS } from 'shared/utils/constants'

import { setPassword } from '../reducers'
import { getNewUser } from '../selectors'
import UserFormLayout from './UserFormLayout'

const passwordLengthValidate = (value) => {
  if (value && value.length < 8) {
    return 'Password must be at least 8 characters'
  }
  if (value && value.length > 128) {
    return 'Password must be no longer than 128 characters'
  }
  return undefined
}

const samePasswordValidate = (value, allValues) => (value === allValues.password ? undefined : 'Passwords do not match')

const PASSWORD_FIELDS = [
  {
    name: 'password',
    label: 'Password',
    validate: passwordLengthValidate,
    type: 'password',
    width: 16,
    inline: true,
  },
  {
    name: 'passwordConfirm',
    label: 'Confirm Password',
    validate: samePasswordValidate,
    type: 'password',
    width: 16,
    inline: true,
  },
]
const FIELDS = [...PASSWORD_FIELDS, ...USER_NAME_FIELDS]

const SetPassword = ({ onSubmit, newUser, location }) => {
  const isReset = queryString.parse(location.search).reset
  return (
    <UserFormLayout
      header={isReset ? 'Reset password' : 'Welcome to seqr'}
      subheader={isReset ? '' : 'Fill out this form to finish setting up your account'}
      onSubmit={onSubmit}
      modalName="set-password"
      fields={isReset ? PASSWORD_FIELDS : FIELDS}
      initialValues={newUser}
    />
  )
}

SetPassword.propTypes = {
  location: PropTypes.object,
  newUser: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  newUser: getNewUser(state),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: updates => dispatch(setPassword({ ...updates, ...ownProps.match.params })),
})

export default connect(mapStateToProps, mapDispatchToProps)(SetPassword)

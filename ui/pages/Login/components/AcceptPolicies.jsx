import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { BooleanCheckbox } from 'shared/components/form/Inputs'
import { validators } from 'shared/components/form/ReduxFormWrapper'

import { updateUserPolicies } from '../reducers'
import UserFormLayout from './UserFormLayout'

const POLICY_FORM_FIELDS = [
  {
    name: 'acceptedPolicies',
    component: BooleanCheckbox,
    validate: validators.required,
    label: (
      <label>
        I accept the &nbsp;
        <Link target="_blank" to="/terms_of_service">Terms of Service</Link>
        &nbsp; and the &nbsp;
        <Link target="_blank" to="/privacy_policy">Privacy Policy</Link>
      </label>
    ),
  },
]

const AcceptPolicies = React.memo(({ onSubmit }) => (
  <UserFormLayout
    header="Seqr Policies"
    subheader="Before continuing to use seqr, please read and accept our policies"
    onSubmit={onSubmit}
    form="acceptPolicies"
    fields={POLICY_FORM_FIELDS}
  />
))

AcceptPolicies.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: updateUserPolicies,
}

export default connect(null, mapDispatchToProps)(AcceptPolicies)

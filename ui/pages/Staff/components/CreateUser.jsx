import React from 'react'
import PropTypes from 'prop-types'
import { Header, Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { USER_NAME_FIELDS } from 'shared/utils/constants'

import { createStaffUser } from '../reducers'

const validateEmail = value => (
  /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i.test(value) ? undefined : 'Invalid email address'
)
const validateBroadEmail = value => (
  /^[A-Z0-9._%+-]+@broadinstitute.org$/i.test(value) ? undefined : 'Cannot grant staff access to non-Broad users'
)

const FIELDS = [
  {
    name: 'email',
    label: 'Email',
    validate: [validateEmail, validateBroadEmail],
    width: 16,
    inline: true,
  },
  ...USER_NAME_FIELDS,
]

const SetPassword = ({ onSubmit }) =>
  <Grid>
    <Grid.Column width={4} />
    <Grid.Column width={8}>
      <Header
        size="large"
        content="Create Staff User"
        subheader="This user will have Manager level access to all projects"
      />
      <ReduxFormWrapper
        onSubmit={onSubmit}
        form="set-password"
        fields={FIELDS}
        successMessage="Staff user was successfully created"
        showErrorPanel
        noModal
      />
    </Grid.Column>
    <Grid.Column width={4} />
  </Grid>

SetPassword.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: createStaffUser,
}

export default connect(null, mapDispatchToProps)(SetPassword)

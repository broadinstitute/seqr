import React from 'react'
import PropTypes from 'prop-types'
import { Modal } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Route, Switch, Link } from 'react-router-dom'

import { updateUserPolicies } from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import { BooleanCheckbox } from '../form/Inputs'
import ReduxFormWrapper, { validators } from '../form/ReduxFormWrapper'

const FORM_FIELDS = [
  {
    name: 'acceptedPolicies',
    component: BooleanCheckbox,
    validate: validators.required,
    label: (
      // eslint-disable-next-line jsx-a11y/label-has-for
      <label>
        I accept the <Link target="_blank" to="/terms_of_service">Terms of Service</Link> and
        the <Link target="_blank" to="/privacy_policy">Privacy Policy</Link>
      </label>
    ),
  },
]

const AcceptPolicies = React.memo(({ user, onSubmit }) =>
  user && Object.keys(user).length && !user.currentPolicies &&
  <Modal open size="small" closeOnDimmerClick={false} closeOnEscape={false}>
    <Modal.Header>Before continuing to use seqr, please read and accept our policies</Modal.Header>
    <Modal.Content>
      <ReduxFormWrapper
        onSubmit={onSubmit}
        noModal
        form="acceptPolicies"
        fields={FORM_FIELDS}
      />
    </Modal.Content>
  </Modal>,
)

AcceptPolicies.propTypes = {
  user: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

const mapDispatchToProps = {
  onSubmit: updateUserPolicies,
}

const NO_POLICIES_PAGES = ['/login', '/matchmaker', '/privacy_policy', '/terms_of_service']

export default () =>
  <Switch>
    {NO_POLICIES_PAGES.map(page =>
      <Route key={page} path={page} component={() => null} />,
    )}
    <Route component={connect(mapStateToProps, mapDispatchToProps)(AcceptPolicies)} />
  </Switch>

import React from 'react'
import PropTypes from 'prop-types'
import Cookies from 'js-cookie'
import { Modal } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Route, Switch, Link } from 'react-router-dom'

import { updateUserPolicies } from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import { BooleanCheckbox } from '../form/Inputs'
import ReduxFormWrapper, { validators } from '../form/ReduxFormWrapper'


const COOKIE_ACTIONS = [{
  primary: true,
  content: 'Accept',
  onClick: () => {
    Cookies.set('accepted_cookies', true)
    window.location.href = window.location.href
  },
}]

const AcceptCookies = () => (
  Cookies.get('accepted_cookies') ? null :
  <Modal
    open
    size="small"
    closeOnDimmerClick={false}
    closeOnEscape={false}
    header="This website uses cookies"
    content={
      <Modal.Content>
        seqr collects cookies to improve our user experience and ensure the secure functioning of our site. For more
        details, see our <Link target="_blank" to="/privacy_policy">Privacy Policy</Link>. By
        clicking &quot;Accept&quot;, you consent to the use of these cookies.
      </Modal.Content>
    }
    actions={COOKIE_ACTIONS}
  />
)


const POLICY_FORM_FIELDS = [
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

// exported for testing purposes only
export const BaseAcceptPolicies = React.memo(({ user, onSubmit }) => (
  (user && Object.keys(user).length && !user.currentPolicies) ?
    <Modal open size="small" closeOnDimmerClick={false} closeOnEscape={false}>
      <Modal.Header>Before continuing to use seqr, please read and accept our policies</Modal.Header>
      <Modal.Content>
        <ReduxFormWrapper
          onSubmit={onSubmit}
          noModal
          form="acceptPolicies"
          fields={POLICY_FORM_FIELDS}
        />
      </Modal.Content>
    </Modal> : <AcceptCookies />
))

BaseAcceptPolicies.propTypes = {
  user: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

const mapDispatchToProps = {
  onSubmit: updateUserPolicies,
}

const NO_COOKIE_PAGES = ['/matchmaker', '/privacy_policy', '/terms_of_service']

const NO_POLICIES_PAGES = ['/login']

export default () =>
  <Switch>
    {NO_COOKIE_PAGES.map(page => <Route key={page} path={page} component={null} />)}
    {NO_POLICIES_PAGES.map(page =>
      <Route key={page} path={page} component={AcceptCookies} />,
    )}
    <Route component={connect(mapStateToProps, mapDispatchToProps)(BaseAcceptPolicies)} />
  </Switch>

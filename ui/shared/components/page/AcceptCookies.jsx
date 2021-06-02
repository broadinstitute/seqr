import React from 'react'
import Cookies from 'js-cookie'
import { Modal } from 'semantic-ui-react'
import { Route, Switch, Link } from 'react-router-dom'

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

const NO_COOKIE_PAGES = ['/matchmaker', '/privacy_policy', '/terms_of_service']

export default () =>
  <Switch>
    {NO_COOKIE_PAGES.map(page => <Route key={page} path={page} component={null} />)}
    <Route component={AcceptCookies} />
  </Switch>

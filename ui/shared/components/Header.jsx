import React from 'react'
import { Grid } from 'semantic-ui-react'

import { computeDashboardUrl } from '../utils/urls'

const Header = ({ user }) =>
  <Grid style={{
    backgroundColor: '#F3F3F3',
    borderStyle: 'solid',
    borderWidth: '0px 0px 1px 0px',
    borderColor: '#E2E2E2',
    paddingTop: '12px' }}
  >
    <Grid.Row>
      <Grid.Column width={1} />
      <Grid.Column
        width={2}
        style={{
          textAlign: 'left',
          paddingLeft: '15px',
          fontSize: 16,
          fontFamily: 'sans-serif',
          fontWeight: 400 }}
      >
        <a href={computeDashboardUrl()}><i>seqr</i></a>
      </ Grid.Column>
      <Grid.Column width={7} />
      <Grid.Column width={3} style={{ textAlign: 'right', fontWeight: 400 }}>
        <b>{user ? (user.email || user.username) : null}</b>
      </ Grid.Column>
      <Grid.Column width={2} style={{ textAlign: 'right' }}>
        <a href="/logout">Log out</a>
      </ Grid.Column>
      <Grid.Column width={1} />
    </Grid.Row>
  </Grid>

Header.propTypes = {
  user: React.PropTypes.object.isRequired,
}

export default Header

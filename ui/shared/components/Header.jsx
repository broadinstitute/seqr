import React from 'react'
import { Grid } from 'semantic-ui-react'
import AwesomeBar from './AwesomeBar'

import { HorizontalSpacer } from './Spacers'

const Header = ({ user }) =>
  <Grid stackable style={{
    backgroundColor: '#F3F3F3',
    borderStyle: 'solid',
    borderWidth: '0px 0px 1px 0px',
    borderColor: '#E2E2E2',
    paddingTop: '12px' }}
  >
    <Grid.Row style={{ padding: '9px' }}>
      <Grid.Column width={1} />
      <Grid.Column width={10} style={{ padding: '0' }}>
        <AwesomeBar />
      </Grid.Column>
      <Grid.Column width={4} style={{ padding: '0', textAlign: 'right' }}>
        <b>{user ? (user.email || user.username) : null}</b>
        <HorizontalSpacer width={30} />
        <a href="/logout">Log out</a>
      </ Grid.Column>
      <Grid.Column width={1} />
    </Grid.Row>
  </Grid>

Header.propTypes = {
  user: React.PropTypes.object.isRequired,
}

export default Header

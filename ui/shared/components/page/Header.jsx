import React from 'react'
import PropTypes from 'prop-types'

import { Grid } from 'semantic-ui-react'
import { computeDashboardUrl } from 'shared/utils/urlUtils'
import { HorizontalSpacer } from 'shared/components/Spacers'

import AwesomeBar from './AwesomeBar'


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
      <Grid.Column width={1} style={{ padding: '6px 5px 0px 10px', verticalAlign: 'bottom' }}>
        <a href={computeDashboardUrl()}>
          <span style={{ fontWeight: 500, fontSize: '16px', fontFamily: 'sans-serif', fontStyle: 'italic' }}>seqr</span>
        </a>
      </Grid.Column>
      <Grid.Column width={9} style={{ padding: '0' }}>
        <AwesomeBar />
      </Grid.Column>
      <Grid.Column width={4} style={{ padding: '6px 0px 0px 0px', textAlign: 'right', whiteSpace: 'nowrap' }}>
        <b>{user ? (user.email || user.username) : null}</b>
        <HorizontalSpacer width={30} />
        <a href="/logout">Log out</a>
      </Grid.Column>
      <Grid.Column width={1} />
    </Grid.Row>
  </Grid>

Header.propTypes = {
  user: PropTypes.object.isRequired,
}

export default Header

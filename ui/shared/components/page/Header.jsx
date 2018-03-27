import React from 'react'
import PropTypes from 'prop-types'

import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { HorizontalSpacer } from 'shared/components/Spacers'
import { getUser } from 'redux/rootReducer'

import AwesomeBar from './AwesomeBar'


const Header = ({ user }) =>
  <Grid stackable style={{
    backgroundColor: '#000',
    borderStyle: 'solid',
    borderWidth: '0 0 0.15em 0',
    borderColor: '#888',
    paddingTop: '12px' }}
  >
    <Grid.Row style={{ padding: '9px' }}>
      <Grid.Column width={1} />
      <Grid.Column width={1} style={{ padding: '6px 5px 0px 10px', verticalAlign: 'bottom' }}>
        <Link to="/dashboard">
          <span style={{ color: 'white', fontWeight: 500, fontSize: '16px', fontFamily: 'sans-serif', fontStyle: 'italic' }}>seqr</span>
        </Link>
      </Grid.Column>
      <Grid.Column width={9} style={{ padding: '0' }}>
        <AwesomeBar />
      </Grid.Column>
      <Grid.Column width={4} style={{ padding: '6px 0px 0px 0px', color: 'white', textAlign: 'right', whiteSpace: 'nowrap' }}>
        Logged in as <b>{user ? (user.email || user.username) : null}</b>
        <HorizontalSpacer width={30} />
        <a href="/logout">
          <span>Log out</span>
        </a>
      </Grid.Column>
      <Grid.Column width={1} />
    </Grid.Row>
  </Grid>

Header.propTypes = {
  user: PropTypes.object.isRequired,
}

// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(Header)

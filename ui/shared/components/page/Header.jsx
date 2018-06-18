import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { HorizontalSpacer } from 'shared/components/Spacers'
import { getUser } from 'redux/rootReducer'

import AwesomeBar from './AwesomeBar'

const HeaderGrid = styled(Grid)`
  background-color: #000;
  border-style: solid;
  border-width: 0 0 0.15em 0;
  border-color: #888;
  padding-top: 12px !important;
`
const HeaderRow = styled(Grid.Row)`
  padding: 9px !important;
`
const DashboardColumn = styled(Grid.Column)`
  padding: 6px 5px 0px 10px;
  vertical-align: bottom;
`
const AwesomeBarColumn = styled(Grid.Column)`
  padding: 0;
`
const UserColumn = styled(Grid.Column)`
  padding: 6px 0px 0px 0px;
  color: white;
  text-align: right;
  white-space: nowrap;
`

const Header = ({ user }) =>
  <HeaderGrid stackable>
    <HeaderRow>
      <Grid.Column width={1} />
      <DashboardColumn width={1}>
        <Link to="/dashboard">
          <span style={{ color: 'white', fontWeight: 500, fontSize: '16px', fontFamily: 'sans-serif', fontStyle: 'italic' }}>seqr</span>
        </Link>
      </DashboardColumn>
      <AwesomeBarColumn width={9}>
        <AwesomeBar />
      </AwesomeBarColumn>
      <UserColumn width={4}>
        Logged in as <b>{user ? (user.email || user.username) : null}</b>
        <HorizontalSpacer width={30} />
        <a href="/logout">
          <span>Log out</span>
        </a>
      </UserColumn>
      <Grid.Column width={1} />
    </HeaderRow>
  </HeaderGrid>

Header.propTypes = {
  user: PropTypes.object.isRequired,
}

// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
})

export { Header as HeaderComponent }

export default connect(mapStateToProps)(Header)

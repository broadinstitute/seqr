import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Menu, Header } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getUser } from 'redux/selectors'

import AwesomeBar from './AwesomeBar'

const HeaderMenu = styled(Menu)`
  padding-left: 100px;
  padding-right: 100px;
`

const PageHeader = ({ user }) =>
  <HeaderMenu borderless inverted attached>
    <Menu.Item as={Link} to="/dashboard"><Header size="medium" inverted>seqr</Header></Menu.Item>
    <Menu.Item as={Link} to="/gene_info" content="Gene Info" />
    <Menu.Item as={Link} to="/gene_lists" content="Gene Lists" />
    <Menu.Item fitted="vertically"><AwesomeBar newWindow inputwidth="350px" /></Menu.Item>
    <Menu.Item position="right">
      <p>Logged in as &nbsp; <b>{user ? (user.email || user.username) : null}</b></p>
    </Menu.Item>
    <Menu.Item as="a" href="/logout">Log out</Menu.Item>
  </HeaderMenu>

PageHeader.propTypes = {
  user: PropTypes.object.isRequired,
}

// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
})

export { PageHeader as PageHeaderComponent }

export default connect(mapStateToProps)(PageHeader)

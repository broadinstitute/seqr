import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Menu, Header } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { googleLogin } from 'pages/Login/reducers'

import AwesomeBar from './AwesomeBar'

const HeaderMenu = styled(Menu)`
  padding-left: 100px;
  padding-right: 100px;
`

const PageHeader = React.memo(({ user }) =>
  <HeaderMenu borderless inverted attached>
    <Menu.Item as={Link} to="/"><Header size="medium" inverted>seqr</Header></Menu.Item>
    {Object.keys(user).length && [
      <Menu.Item key="gene" as={Link} to="/gene_info" content="Gene Info" />,
      <Menu.Item key="gene_lists" as={Link} to="/gene_lists" content="Gene Lists" />,
      user.isStaff ? <Menu.Item key="staff" as={Link} to="/staff" content="Staff Pages" /> : null,
      <Menu.Item key="awesomebar" fitted="vertically"><AwesomeBar newWindow inputwidth="350px" /></Menu.Item>,
      <Menu.Item key="user" position="right">
        <p>Logged in as &nbsp; <b>{user && (user.displayName || user.email) + (user.isAnvil ? ' with AnVIL' : '')}</b></p>
      </Menu.Item>,
      user.anvilEmail ?
        <Menu.Item key="connect_anvil" content={!user.isAnvil && `Connected AnVIL email: ${user.anvilEmail}`} /> :
        <Menu.Item key="connect_anvil" content="Connect AnVIL email" onClick={googleLogin} />,
      <Menu.Item key="logout" as="a" href="/logout">Log out</Menu.Item>,
    ]}
  </HeaderMenu>,
)

PageHeader.propTypes = {
  user: PropTypes.object,
}

// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
})

export { PageHeader as PageHeaderComponent }

export default connect(mapStateToProps)(PageHeader)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Menu, Header } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import MessagesPanel from 'shared/components/form/MessagesPanel'
import { googleLogin } from 'pages/Login/components/Login'

import AwesomeBar from './AwesomeBar'

const HeaderMenu = styled(Menu)`
  padding-left: 100px;
  padding-right: 100px;
`

const MESSAGE_FIELD = user => [{
  name: 'anvilUsername',
  info: [user.anvilUsername ? `${user.anvilUsername}` : 'AnVIL user is not configured'],
  component: MessagesPanel,
  width: 16,
},
]

const PageHeader = React.memo(({ user }) =>
  <HeaderMenu borderless inverted attached>
    <Menu.Item as={Link} to="/"><Header size="medium" inverted>seqr</Header></Menu.Item>
    {Object.keys(user).length && [
      <Menu.Item key="gene" as={Link} to="/gene_info" content="Gene Info" />,
      <Menu.Item key="gene_lists" as={Link} to="/gene_lists" content="Gene Lists" />,
      user.isStaff ? <Menu.Item key="staff" as={Link} to="/staff" content="Staff Pages" /> : null,
      <Menu.Item key="awesomebar" fitted="vertically"><AwesomeBar newWindow inputwidth="350px" /></Menu.Item>,
      <Menu.Item key="user" position="right">
        <p>Logged in as &nbsp; <b>{user ? (user.displayName || user.email) : null}</b></p>
      </Menu.Item>,
      user.isAnvil ? null : <UpdateButton
        modalId="editAnvilUser"
        modalTitle={`${user.displayName}'s AnVIL Account`}
        formFields={MESSAGE_FIELD(user)}
        initialValues={user}
        onSubmit={googleLogin}
        submitButtonText="Change"
        showErrorPanel
        size="tiny"
      />,
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

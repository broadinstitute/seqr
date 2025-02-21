import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Menu, Header, Dropdown } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { updateUser } from 'redux/rootReducer'
import { getUser, getOauthLoginProvider } from 'redux/selectors'
import { USER_NAME_FIELDS, LOCAL_LOGIN_URL, FEATURE_UPDATES_PATH } from 'shared/utils/constants'
import UpdateButton from '../buttons/UpdateButton'

import AwesomeBar from './AwesomeBar'

const HeaderMenu = styled(Menu)`
  padding-left: 100px;
  padding-right: 100px;
`

const PageHeader = React.memo(({ user, oauthLoginProvider, onSubmit }) => {
  const loginUrl = oauthLoginProvider ? `/login/${oauthLoginProvider}` : LOCAL_LOGIN_URL

  return (
    <HeaderMenu borderless inverted attached>
      <Menu.Item as={Link} to="/"><Header size="medium" inverted>seqr</Header></Menu.Item>
      {Object.keys(user).length ? [
        <Menu.Item key="search" as={Link} to="/variant_search" content="Search" />,
        <Menu.Item key="summary_data" as={Link} to="/summary_data" content="Summary Data" />,
        (user.isAnalyst || user.isPm) ? <Menu.Item key="report" as={Link} to="/report" content="Reports" /> : null,
        (user.isDataManager || user.isPm) ? <Menu.Item key="data_management" as={Link} to="/data_management" content="Data Management" /> : null,
        <Menu.Item key="awesomebar" fitted="vertically"><AwesomeBar newWindow inputwidth="350px" /></Menu.Item>,
      ] : null }
      <Menu.Item key="spacer" position="right" />
      <Menu.Item key="feature_updates" as={Link} to={FEATURE_UPDATES_PATH} content="Feature Updates" />
      {Object.keys(user).length ? [
        <Dropdown
          item
          key="user"
          trigger={
            <span>
              Logged in as &nbsp;
              <b>{user.displayName || user.email}</b>
            </span>
          }
        >
          <Dropdown.Menu>
            <UpdateButton
              trigger={<Dropdown.Item icon="write" text="Edit User Info" />}
              modalId="updateUser"
              modalTitle="Edit User Info"
              initialValues={user}
              formFields={USER_NAME_FIELDS}
              onSubmit={onSubmit}
            />
          </Dropdown.Menu>
        </Dropdown>,
        <Menu.Item key="logout" as="a" href="/logout">Log out</Menu.Item>,
      ] :
      <Menu.Item as="a" href={loginUrl}>Log in</Menu.Item> }
    </HeaderMenu>
  )
})

PageHeader.propTypes = {
  user: PropTypes.object,
  oauthLoginProvider: PropTypes.string,
  onSubmit: PropTypes.func,
}

// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
  oauthLoginProvider: getOauthLoginProvider(state),
})

const mapDispatchToProps = {
  onSubmit: updateUser,
}

export { PageHeader as PageHeaderComponent }

export default connect(mapStateToProps, mapDispatchToProps)(PageHeader)

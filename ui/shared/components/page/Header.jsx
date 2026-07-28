import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Menu, Header, Dropdown, Label } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { updateUser } from 'redux/rootReducer'
import { getUser, getOauthLoginProvider, getLastFeatureUpdate } from 'redux/selectors'
import { USER_NAME_FIELDS, LOCAL_LOGIN_URL, FEATURE_UPDATES_PATH } from 'shared/utils/constants'
import UpdateButton from '../buttons/UpdateButton'

import AwesomeBar from './AwesomeBar'

const HeaderMenu = styled(Menu)`
  padding-left: 100px;
  padding-right: 100px;

  /* 
    @elanfisher:
    The nav items need ~1780px at the default gutters, so on smaller screens
    or when the page is zoomed the right hand items (eg. "Log out") were
    clipped and thus occluded. Shifted the gutters and search box and then allowed 
    the bar to wrap rather than overflow.
  */
  @media (max-width: 1800px) {
    padding-left: 24px;
    padding-right: 24px;
  }

  /*
    @elanfisher: 
    Flexbox wraps before it shrinks, so only allow wrapping once the search box
    has run out of room to give. Above this the bar stays on one line. 
  */
  @media (max-width: 1400px) {
    flex-wrap: wrap;
  }

  /* 
    @elanfisher:
    Keep the search box at its full 350px whenever it fits, and let it be the
    first thing to give way when it does not. The basis and max are 382px,
    350px of search plus the menu item's own 2 x 16px padding, so users who
    were never short of space see exactly the previous layout.
  */
  .item.awesomebar {
    flex: 0 1 382px;
    min-width: 216px;
    max-width: 382px;
  }

  .item.awesomebar .ui.search {
    width: 100%;
  }
`

const PageHeader = React.memo(({ user, oauthLoginProvider, onSubmit, lastFeatureUpdate }) => {
  const loginUrl = oauthLoginProvider ? `/login/${oauthLoginProvider}` : LOCAL_LOGIN_URL

  return (
    <HeaderMenu borderless inverted attached>
      <Menu.Item as={Link} to="/"><Header size="medium" inverted>seqr</Header></Menu.Item>
      {Object.keys(user).length ? [
        <Menu.Item key="search" as={Link} to="/variant_search" content="Search" />,
        <Menu.Item key="variant_lookup" as={Link} to="/variant_lookup" content="Variant Lookup" />,
        <Menu.Item key="gene_lookup" as={Link} to="/variant_lookup/gene" content="Gene Lookup" />,
        <Menu.Item key="summary_data" as={Link} to="/summary_data" content="Summary Data" />,
        (user.isAnalyst || user.isPm) ? <Menu.Item key="report" as={Link} to="/report" content="Reports" /> : null,
        (user.isDataManager || user.isPm) ? <Menu.Item key="data_management" as={Link} to="/data_management" content="Data Management" /> : null,
        // @elanfisher: Made the searchbar flex properly rather than be fixed at 350px.
        <Menu.Item key="awesomebar" className="awesomebar" fitted="vertically"><AwesomeBar newWindow inputwidth="350px" /></Menu.Item>,
      ] : null }
      <Menu.Item key="spacer" position="right" />
      <Menu.Item key="feature_updates">
        <Link to={FEATURE_UPDATES_PATH}>Feature Updates</Link>
        {(lastFeatureUpdate && (new Date()).setMonth(new Date().getMonth() - 1) < new Date(lastFeatureUpdate)) &&
          <Label color="red" pointing="left" size="tiny">New</Label>}
      </Menu.Item>
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
            {/* @elanfisher: I moved the "Log Out" button into this drop down as it seemed
            to fit a bit nicer here and reduce the header clutter. */}
            <Dropdown.Item as="a" href="/logout" icon="sign out" text="Log out" />
          </Dropdown.Menu>
        </Dropdown>,
      ] :
      <Menu.Item as="a" href={loginUrl}>Log in</Menu.Item> }
    </HeaderMenu>
  )
})

PageHeader.propTypes = {
  user: PropTypes.object,
  oauthLoginProvider: PropTypes.string,
  onSubmit: PropTypes.func,
  lastFeatureUpdate: PropTypes.string,
}

// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
  oauthLoginProvider: getOauthLoginProvider(state),
  lastFeatureUpdate: getLastFeatureUpdate(state),
})

const mapDispatchToProps = {
  onSubmit: updateUser,
}

export { PageHeader as PageHeaderComponent }

export default connect(mapStateToProps, mapDispatchToProps)(PageHeader)

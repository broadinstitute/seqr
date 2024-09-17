import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon, Button } from 'semantic-ui-react'
import Cookies from 'js-cookie'
import { getHijakEnabled } from 'redux/selectors'
import DataTable from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { getAllUsers, getAllUsersLoading } from '../selectors'
import { loadAllUsers } from '../reducers'

const CheckIcon = () => <Icon color="green" name="check circle" />
const XIcon = () => <Icon color="red" name="times circle" />

const hasFieldColumn = (name, content) => (
  { name, content, noFormatExport: true, format: val => (val[name] ? <CheckIcon /> : <XIcon />) }
)

const hasPrivilegeColumn = (name, content) => (
  { name, content, noFormatExport: true, format: val => (val[name] && val.isActive && <CheckIcon />) }
)

const COLUMNS = [
  { name: 'email', content: 'Email' },
  { name: 'displayName', content: 'Name' },
  { name: 'username', content: 'Username' },
  { name: 'dateJoined', content: 'Date Joined', format: ({ dateJoined }) => (dateJoined || '').slice(0, 10) },
  { name: 'lastLogin', content: 'Last Login', format: ({ lastLogin }) => (lastLogin || '').slice(0, 10) },
  hasFieldColumn('hasCloudAuth', 'OAuth?'),
  hasPrivilegeColumn('isAnalyst', 'Analyst?'),
  hasPrivilegeColumn('isPm', 'PM?'),
  hasPrivilegeColumn('isDataManager', 'Data Manager?'),
  hasPrivilegeColumn('isSuperuser', 'Superuser?'),
  hasFieldColumn('isActive', 'Active?'),
]

const hijakLogIn = (e, { value }) => {
  const hijackFormData = new FormData()
  hijackFormData.append('user_pk', value.id)
  hijackFormData.append('next', '/')
  fetch(
    '/hijack/acquire/', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': Cookies.get('csrf_token'),
      },
      body: hijackFormData,
    },
  ).then((response) => { window.location.href = response.url })
}

const HIJAK_COLUMNS = [
  ...COLUMNS,
  { name: 'id', format: val => <Button content="Log In" value={val} onClick={hijakLogIn} /> },
]

const getUserFilterVal = ({ email, displayName }) => `${email}-${displayName}`

const Users = React.memo(({ users, loading, load, hijak }) => (
  <DataLoader load={load} content loading={false}>
    <DataTable
      striped
      idField="username"
      defaultSortColumn="email"
      loading={loading}
      data={users}
      columns={hijak ? HIJAK_COLUMNS : COLUMNS}
      getRowFilterVal={getUserFilterVal}
      downloadFileName="users"
      downloadAlign="1em"
    />
  </DataLoader>
))

Users.propTypes = {
  users: PropTypes.arrayOf(PropTypes.object),
  loading: PropTypes.bool,
  load: PropTypes.func,
  hijak: PropTypes.bool,
}

const mapStateToProps = state => ({
  users: getAllUsers(state),
  loading: getAllUsersLoading(state),
  hijak: getHijakEnabled(state),
})

const mapDispatchToProps = {
  load: loadAllUsers,
}

export default connect(mapStateToProps, mapDispatchToProps)(Users)

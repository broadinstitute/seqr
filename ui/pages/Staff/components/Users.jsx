import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon, Button } from 'semantic-ui-react'

import { loadUserOptions } from 'redux/rootReducer'
import { getAllUsers, getUserOptionsIsLoading, getHijakEnabled } from 'redux/selectors'
import DataTable from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'

const CheckIcon = () => <Icon color="green" name="check circle" />

const COLUMNS = [
  { name: 'email', content: 'Email' },
  { name: 'displayName', content: 'Name' },
  { name: 'username', content: 'Username' },
  { name: 'dateJoined', content: 'Date Joined', format: ({ dateJoined }) => (dateJoined || '').slice(0, 10) },
  { name: 'lastLogin', content: 'Last Login', format: ({ lastLogin }) => (lastLogin || '').slice(0, 10) },
  { name: 'isStaff', content: 'Staff?', format: val => (val.isStaff && val.isActive && <CheckIcon />) },
  {
    name: 'isActive',
    content: 'Active?',
    format: val => (val.isActive ? <CheckIcon /> : <Icon color="red" name="times circle" />),
  },
]

const HIJAK_COLUMNS = [
  ...COLUMNS,
  {
    name: 'id',
    format: val =>
      <Button
        content="Log In"
        onClick={() => fetch(
          `/hijack/${val.id}/`, { method: 'POST', credentials: 'include' },
        ).then((response) => { window.location.href = response.url })}
      />,
  },
]

const getUserFilterVal = ({ email, displayName }) => `${email}-${displayName}`

const Users = React.memo(({ users, loading, load, hijak }) =>
  <DataLoader load={load} content loading={false}>
    <DataTable
      striped
      idField="username"
      defaultSortColumn="email"
      loading={loading}
      data={users}
      columns={hijak ? HIJAK_COLUMNS : COLUMNS}
      getRowFilterVal={getUserFilterVal}
    />
  </DataLoader>,
)

Users.propTypes = {
  users: PropTypes.array,
  loading: PropTypes.bool,
  load: PropTypes.func,
  hijak: PropTypes.bool,
}


const mapStateToProps = state => ({
  users: getAllUsers(state),
  loading: getUserOptionsIsLoading(state),
  hijak: getHijakEnabled(state),
})

const mapDispatchToProps = {
  load: loadUserOptions,
}

export default connect(mapStateToProps, mapDispatchToProps)(Users)

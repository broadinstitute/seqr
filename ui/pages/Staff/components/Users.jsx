import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon, Button } from 'semantic-ui-react'

import { loadUserOptions } from 'redux/rootReducer'
import { getAllUsers, getUserOptionsIsLoading } from 'redux/selectors'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'

const COLUMNS = [
  { name: 'email', content: 'Email' },
  { name: 'displayName', content: 'Name' },
  { name: 'username', content: 'Username' },
  { name: 'dateJoined', content: 'Date Joined', format: ({ dateJoined }) => (dateJoined || '').slice(0, 10) },
  { name: 'lastLogin', content: 'Last Login', format: ({ lastLogin }) => (lastLogin || '').slice(0, 10) },
  { name: 'isStaff', content: 'Staff?', format: val => (val.isStaff && <Icon color="green" name="check circle" />) },
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

const Users = ({ users, loading, load }) =>
  <DataLoader load={load} content loading={false}>
    <SortableTable
      striped
      idField="username"
      defaultSortColumn="email"
      loading={loading}
      data={users}
      columns={COLUMNS}
      getRowFilterVal={getUserFilterVal}
    />
  </DataLoader>

Users.propTypes = {
  users: PropTypes.array,
  loading: PropTypes.bool,
  load: PropTypes.func,
}


const mapStateToProps = state => ({
  users: getAllUsers(state),
  loading: getUserOptionsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadUserOptions,
}

export default connect(mapStateToProps, mapDispatchToProps)(Users)

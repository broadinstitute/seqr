import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import StateDataLoader from 'shared/components/StateDataLoader'
import { getCurrentProject } from '../selectors'

const ProjectNotifications = React.memo(({ notifications }) => (
  <div>
    {notifications.map(({ verb, timestamp }) => (
      <div>{`${verb} on ${new Date(timestamp).toLocaleDateString()}`}</div>
    ))}
  </div>
))

ProjectNotifications.propTypes = {
  notifications: PropTypes.arrayOf(PropTypes.object),
}

const mapStateToProps = (state) => {
  const { canEdit, workspaceName, collaborators, collaboratorGroups } = getCurrentProject(state)
  return {
    canEdit,
    workspaceName,
    collaborators,
    collaboratorGroups,
    user: getUser(state),
  }
}

const parseResponse = response => ({ notifications: response.unread_list })

// TODO need to query for the current project only, handle if user is not a subscriber but updates exist
export default connect(mapStateToProps)(props => (
  <StateDataLoader
    url="/notifications/api/unread_list"
    childComponent={ProjectNotifications}
    parseResponse={parseResponse}
    {...props}
  />
))

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import StateDataLoader from 'shared/components/StateDataLoader'
import { getCurrentProject } from '../selectors'

// TODO add subscribe button for non-subscribers
// TODO ability to mark unread as read
// TODO add read count, ability to see read notifications

const ProjectNotifications = React.memo(({ unreadNotifications }) => (
  <div>
    {unreadNotifications.map(({ verb, timestamp }) => (
      <div>{`${verb} on ${new Date(timestamp).toLocaleDateString()}`}</div>
    ))}
  </div>
))

ProjectNotifications.propTypes = {
  unreadNotifications: PropTypes.arrayOf(PropTypes.object),
}

const mapStateToProps = state => ({
  project: getCurrentProject(state), // TODO only need guid?
  user: getUser(state),
})

const parseResponse = response => response

const LoadedProjectNotifications = ({ project, ...props }) => (
  <StateDataLoader
    url={`/api/project/${project.projectGuid}/get_notification`}
    childComponent={ProjectNotifications}
    parseResponse={parseResponse}
    {...props}
  />
)

LoadedProjectNotifications.propTypes = {
  project: PropTypes.object,
}

export default connect(mapStateToProps)(LoadedProjectNotifications)

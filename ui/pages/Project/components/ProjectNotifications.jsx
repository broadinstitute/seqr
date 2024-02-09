import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Feed } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import StateDataLoader from 'shared/components/StateDataLoader'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getCurrentProject } from '../selectors'

// TODO add subscribe button for non-subscribers

const setPath = (setUrlPath, path) => () => setUrlPath(path)

const ProjectNotifications = React.memo(({ readNotifications, unreadNotifications, readCount, setUrlPath }) => {
  const hasUnread = unreadNotifications?.length > 0
  const notifications = hasUnread ? unreadNotifications : readNotifications
  let buttonProps
  if (hasUnread) {
    buttonProps = { path: 'mark_read', content: 'Mark all as read', icon: 'calendar check outline' }
  } else if (readCount && !readNotifications) {
    buttonProps = { path: 'read', content: `Show ${readCount} read notifications`, icon: 'history' }
  }
  return (
    <Feed>
      {notifications ? notifications.map(({ verb, timestamp, id }) => (
        <Feed.Event key={id}>
          <Feed.Content><Feed.Summary date={new Date(timestamp).toLocaleDateString()} content={verb} /></Feed.Content>
        </Feed.Event>
      )) : <Feed.Event><i>No new notifications</i></Feed.Event>}
      {buttonProps && (
        <ButtonLink
          onClick={setPath(setUrlPath, buttonProps.path)}
          content={buttonProps.content}
          icon={buttonProps.icon}
        />
      )}
    </Feed>
  )
})

ProjectNotifications.propTypes = {
  readNotifications: PropTypes.arrayOf(PropTypes.object),
  unreadNotifications: PropTypes.arrayOf(PropTypes.object),
  readCount: PropTypes.number,
  setUrlPath: PropTypes.func,
}

const mapStateToProps = state => ({
  project: getCurrentProject(state), // TODO only need guid?
  user: getUser(state),
})

const parseResponse = response => response

const LoadedProjectNotifications = ({ project, ...props }) => {
  const [urlPath, setUrlPath] = useState('unread')
  return (
    <StateDataLoader
      url={`/api/project/${project.projectGuid}/notifications/${urlPath}`}
      childComponent={ProjectNotifications}
      parseResponse={parseResponse}
      setUrlPath={setUrlPath}
      {...props}
    />
  )
}

LoadedProjectNotifications.propTypes = {
  project: PropTypes.object,
}

export default connect(mapStateToProps)(LoadedProjectNotifications)

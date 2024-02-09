import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Feed } from 'semantic-ui-react'

import StateDataLoader from 'shared/components/StateDataLoader'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getProjectGuid } from '../selectors'

const setPath = (setUrlPath, path) => () => setUrlPath(path)

const ProjectNotifications = React.memo((
  { readNotifications, unreadNotifications, readCount, isSubscriber, setUrlPath },
) => {
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
          <Feed.Content><Feed.Summary date={timestamp} content={verb} /></Feed.Content>
        </Feed.Event>
      )) : <Feed.Event><i>No new notifications</i></Feed.Event>}
      {buttonProps && (
        <Feed.Event>
          <ButtonLink
            onClick={setPath(setUrlPath, buttonProps.path)}
            content={buttonProps.content}
            icon={buttonProps.icon}
          />
        </Feed.Event>
      )}
      {!isSubscriber && (
        <Feed.Event>
          <ButtonLink onClick={setPath(setUrlPath, 'subscribe')} content="Subscribe" icon="calendar plus outline" />
        </Feed.Event>
      )}
    </Feed>
  )
})

ProjectNotifications.propTypes = {
  readNotifications: PropTypes.arrayOf(PropTypes.object),
  unreadNotifications: PropTypes.arrayOf(PropTypes.object),
  readCount: PropTypes.number,
  isSubscriber: PropTypes.bool,
  setUrlPath: PropTypes.func,
}

const mapStateToProps = state => ({
  projectGuid: getProjectGuid(state),
})

const parseResponse = response => response

const LoadedProjectNotifications = ({ projectGuid, ...props }) => {
  const [urlPath, setUrlPath] = useState('unread')
  return (
    <StateDataLoader
      url={`/api/project/${projectGuid}/notifications/${urlPath}`}
      childComponent={ProjectNotifications}
      parseResponse={parseResponse}
      setUrlPath={setUrlPath}
      {...props}
    />
  )
}

LoadedProjectNotifications.propTypes = {
  projectGuid: PropTypes.string,
}

export default connect(mapStateToProps)(LoadedProjectNotifications)

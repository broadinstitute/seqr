import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Feed } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import StateDataLoader from 'shared/components/StateDataLoader'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getCurrentProject } from '../selectors'

// TODO add subscribe button for non-subscribers
// TODO ability to mark unread as read
// TODO add read count, ability to see read notifications

const setPath = (setUrlPath, path) => () => setUrlPath(path)

const ProjectNotifications = React.memo(({ unreadNotifications, setUrlPath }) => (
  <Feed>
    {unreadNotifications?.map(({ verb, timestamp, id }) => (
      <Feed.Event key={id}>
        <Feed.Content><Feed.Summary date={new Date(timestamp).toLocaleDateString()} content={verb} /></Feed.Content>
      </Feed.Event>
    ))}
    {unreadNotifications?.length > 0 && (
      <ButtonLink
        onClick={setPath(setUrlPath, 'mark_read')}
        content="Mark all as read"
        icon="calendar check outline"
      />
    )}
  </Feed>
))

ProjectNotifications.propTypes = {
  unreadNotifications: PropTypes.arrayOf(PropTypes.object),
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

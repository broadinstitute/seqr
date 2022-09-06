import React from 'react'
import PropTypes from 'prop-types'
import { Message, Segment } from 'semantic-ui-react'

import LoadWorkspaceDataForm from 'shared/components/panel/LoadWorkspaceDataForm'

export const WorkspaceAccessError = ({ match }) => (
  <Segment basic padded="very" textAlign="center">
    <Message error compact size="large">
      <Message.Header>
        User does not have sufficient permissions to load data from &nbsp;
        {`"${match.params.workspaceNamespace}/${match.params.workspaceName}"`}
      </Message.Header>
      <Message.List>
        To submit the initial request to load data to seqr, users require:
        <Message.Item>&quot;Writer&quot; or &quot;Owner&quot; level access to the workspace</Message.Item>
        <Message.Item>The &quot;Can Share&quot; permission enabled for the workspace</Message.Item>
        <Message.Item>
          No &nbsp;
          <a href="https://support.terra.bio/hc/en-us/articles/360026775691" target="_blank" rel="noreferrer">
            authorization domains
          </a>
          &nbsp; to be associated with the workspace
        </Message.Item>
      </Message.List>
    </Message>
  </Segment>
)

WorkspaceAccessError.propTypes = {
  match: PropTypes.object,
}

const LoadWorkspaceData = ({ match }) => (
  <div>
    <LoadWorkspaceDataForm params={match.params} />
  </div>
)

LoadWorkspaceData.propTypes = {
  match: PropTypes.object,
}

export default LoadWorkspaceData

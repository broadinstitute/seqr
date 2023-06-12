import React from 'react'
import PropTypes from 'prop-types'
import { Message, Segment } from 'semantic-ui-react'

import LoadWorkspaceDataForm, { WORKSPACE_REQUIREMENTS } from 'shared/components/panel/LoadWorkspaceDataForm'

export const WorkspaceAccessError = ({ match }) => (
  <Segment basic padded="very" textAlign="center">
    <Message error compact size="large">
      <Message.Header>
        User does not have sufficient permissions to load data from &nbsp;
        {`"${match.params.workspaceNamespace}/${match.params.workspaceName}"`}
      </Message.Header>
      <Message.List>
        To submit the initial request to load data to seqr, users require:
        {WORKSPACE_REQUIREMENTS.map(item => <Message.Item>{item}</Message.Item>)}
      </Message.List>
    </Message>
  </Segment>
)

WorkspaceAccessError.propTypes = {
  match: PropTypes.object,
}

const LoadWorkspaceData = ({ match }) => (
  <div>
    <LoadWorkspaceDataForm params={match.params} createProject />
  </div>
)

LoadWorkspaceData.propTypes = {
  match: PropTypes.object,
}

export default LoadWorkspaceData

import React from 'react'
import DocumentTitle from 'react-document-title'
import PropTypes from 'prop-types'
import { Message, Segment } from 'semantic-ui-react'

import LoadWorkspaceDataForm from './components/LoadWorkspaceDataForm'

export const WorkspaceAccessError = ({ match }) =>
  <Segment basic padded="very" textAlign="center">
    <Message error compact size="large" >
      <Message.Header>
        User does not have sufficient permissions for workspace &quot;{match.params.name}&quot;
      </Message.Header>
      <Message.List>
        To submit the initial request to load data to seqr, users require:
        <Message.Item>&quot;Writer&quot; or &quot;Owner&quot; level access to the workspace</Message.Item>
        <Message.Item>The &quot;Can Share&quot; permission enabled for the workspace</Message.Item>
      </Message.List>
    </Message>
  </Segment>

WorkspaceAccessError.propTypes = {
  match: PropTypes.object,
}

const LoadWorkspaceData = ({ match }) =>
  (
    <div>
      <DocumentTitle title="seqr: load anvil data" />
      <LoadWorkspaceDataForm
        namespace={match.params.namespace}
        name={match.params.name}
      />
    </div>
  )

LoadWorkspaceData.propTypes = {
  match: PropTypes.object,
}

export default LoadWorkspaceData

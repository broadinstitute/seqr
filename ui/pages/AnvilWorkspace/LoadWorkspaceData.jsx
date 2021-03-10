import React from 'react'
import DocumentTitle from 'react-document-title'
import PropTypes from 'prop-types'
import { Message, Segment } from 'semantic-ui-react'

import LoadWorkspaceDataForm from './components/LoadWorkspaceDataForm'

export const WorkspaceAccessError = ({ match }) =>
  <Segment basic padded="very" textAlign="center">
    <Message error compact size="large" content={`User does not have sufficient permissions for workspace ${match.params.name}`} />
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

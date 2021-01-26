import React from 'react'
import DocumentTitle from 'react-document-title'
import PropTypes from 'prop-types'

import LoadWorkspaceDataForm from './components/LoadWorkspaceDataForm'

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

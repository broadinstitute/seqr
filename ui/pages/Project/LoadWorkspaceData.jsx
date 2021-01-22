import React from 'react'
import DocumentTitle from 'react-document-title'
import PropTypes from 'prop-types'

import { BASE_UPLOAD_FORMATS } from './components/edit-families-and-individuals/BulkEditForm'
import LoadWorkspaceDataForm from './components/LoadWorkspaceDataForm'
import { INDIVIDUAL_CORE_EXPORT_DATA, INDIVIDUAL_ID_EXPORT_DATA } from './constants'

const LoadWorkspaceData = ({ match }) =>
  (
    <div>
      <DocumentTitle title="seqr: home" />
      <LoadWorkspaceDataForm
        name="individuals"
        actionDescription="load individual data from an AnVIL workspace to a new seqr project"
        details={
          <div>
            The individual IDs need to match the VCF ids.
          </div>
        }
        requiredFields={INDIVIDUAL_ID_EXPORT_DATA}
        optionalFields={INDIVIDUAL_CORE_EXPORT_DATA}
        uploadFormats={BASE_UPLOAD_FORMATS}
        workspace={match.params.workspace}
        modalName="LoadWorkspaceData"
        onSubmit={() => 'to be completed'}
      />
    </div>
  )

LoadWorkspaceData.propTypes = {
  match: PropTypes.object,
}

export default LoadWorkspaceData

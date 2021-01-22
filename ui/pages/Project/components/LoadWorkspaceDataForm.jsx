import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import ReduxFormWrapper, { configuredField } from 'shared/components/form/ReduxFormWrapper'
import { BaseBulkContent } from './edit-families-and-individuals/BulkEditForm'
import { getEntityExportConfig } from '../selectors'

const FILE_FIELD_NAME = 'uploadedFile'

const mapStateToProps = (state, ownProps) => ({
  blankExportConfig: getEntityExportConfig({ name: ownProps.workspace }, [], null, 'template', ownProps.requiredFields.concat(ownProps.optionalFields)),
})

const LoadWorkspaceContent = connect(mapStateToProps)(BaseBulkContent)

const LOAD_PROJECT_DESC = { name: 'description', label: 'Project Description', placeholder: 'Description' }

const LoadWorkspaceDataForm = React.memo(({ name, modalName, onSubmit, ...props }) =>
  <ReduxFormWrapper
    form={`loadWorkspaceData_${name}`}
    modalName={modalName}
    onSubmit={values => onSubmit(values[FILE_FIELD_NAME])}
    confirmCloseIfNotSaved
    closeOnSuccess
    showErrorPanel
    liveValidate
    size="small"
  >
    {configuredField(LOAD_PROJECT_DESC)}
    <LoadWorkspaceContent name={name} {...props} />
  </ReduxFormWrapper>,
)

LoadWorkspaceDataForm.propTypes = {
  name: PropTypes.string.isRequired,
  modalName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
}

export default LoadWorkspaceDataForm

import React from 'react'
import PropTypes from 'prop-types'

import { FILE_FIELD_NAME, PROJECT_DESC_FIELDS, FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID } from 'shared/utils/constants'
import { BaseBulkContent, BASE_UPLOAD_FORMATS } from 'pages/Project/components/edit-families-and-individuals/BulkEditForm'
import { INDIVIDUAL_CORE_EXPORT_DATA, INDIVIDUAL_ID_EXPORT_DATA } from 'pages/Project/constants'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'

const FIELD_DESCRIPTIONS = {
  [FAMILY_FIELD_ID]: 'Family ID of the individual',
  [INDIVIDUAL_FIELD_ID]: 'ID of the Individual (needs to match the VCF ids)',
}
const REQUIRED_FIELDS = INDIVIDUAL_ID_EXPORT_DATA.map(config => (
  { ...config, description: FIELD_DESCRIPTIONS[config.field] }))

const BLANK_EXPORT = {
  filename: 'individuals_template',
  rawData: [],
  headers: [...INDIVIDUAL_ID_EXPORT_DATA, ...INDIVIDUAL_CORE_EXPORT_DATA].map(config => config.header), // or whatever our field constants are
  processRow: val => val,
}

const UPLOAD_PEDIGREE_FIELD = {
  name: FILE_FIELD_NAME,
  component: BaseBulkContent,
  blankExportConfig: BLANK_EXPORT,
  requiredFields: REQUIRED_FIELDS,
  optionalFields: INDIVIDUAL_CORE_EXPORT_DATA,
  uploadFormats: BASE_UPLOAD_FORMATS,
  actionDescription: 'load individual data from an AnVIL workspace to a new seqr project',
  url: '/api/create_project_from_workspace/upload_individuals_table',
  //Todo: add validate: validateUploadedFile, // from 'shared/components/form/XHRUploaderField'
}

const FORM_FIELDS = [PROJECT_DESC_FIELDS, UPLOAD_PEDIGREE_FIELD]

const LoadWorkspaceDataForm = React.memo(({ namespace, name }) =>
  <ReduxFormWrapper
    form="loadWorkspaceData"
    modalName="loadWorkspaceData"
    onSubmit={values => console.log(values, namespace, name)}
    confirmCloseIfNotSaved
    closeOnSuccess
    showErrorPanel
    liveValidate
    size="small"
    fields={FORM_FIELDS}
  />,
)

LoadWorkspaceDataForm.propTypes = {
  namespace: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
}

export default LoadWorkspaceDataForm

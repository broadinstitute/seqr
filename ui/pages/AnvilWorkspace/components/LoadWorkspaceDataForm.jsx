import React from 'react'
import PropTypes from 'prop-types'
import { Header, Segment } from 'semantic-ui-react'
import { SubmissionError } from 'redux-form'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

import { FILE_FIELD_NAME, PROJECT_DESC_FIELD, GENOME_VERSION_FIELD, FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID } from 'shared/utils/constants'
import { BaseBulkContent, BASE_UPLOAD_FORMATS } from 'pages/Project/components/edit-families-and-individuals/BulkEditForm'
import { INDIVIDUAL_CORE_EXPORT_DATA, INDIVIDUAL_ID_EXPORT_DATA } from 'pages/Project/constants'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { BooleanCheckbox } from 'shared/components/form/Inputs'

const FIELD_DESCRIPTIONS = {
  [FAMILY_FIELD_ID]: 'Family ID',
  [INDIVIDUAL_FIELD_ID]: 'Individual ID (needs to match the VCF ids)',
}
const REQUIRED_FIELDS = INDIVIDUAL_ID_EXPORT_DATA.map(config => (
  { ...config, description: FIELD_DESCRIPTIONS[config.field] }))

const BLANK_EXPORT = {
  filename: 'individuals_template',
  rawData: [],
  headers: [...INDIVIDUAL_ID_EXPORT_DATA, ...INDIVIDUAL_CORE_EXPORT_DATA].map(config => config.header),
  processRow: val => val,
}

const UploadPedigreeField = React.memo(() =>
  [
    // eslint-disable-next-line jsx-a11y/label-has-for
    <label key="uploadLabel">Upload Pedigree Data</label>,
    <Segment key="uploadForm">
      <BaseBulkContent
        blankExportConfig={BLANK_EXPORT}
        requiredFields={REQUIRED_FIELDS}
        optionalFields={INDIVIDUAL_CORE_EXPORT_DATA}
        uploadFormats={BASE_UPLOAD_FORMATS}
        actionDescription="load individual data from an AnVIL workspace to a new seqr project"
        url="/api/upload_temp_file"
      />
    </Segment>,
  ],
)

const UPLOAD_PEDIGREE_FIELD = {
  name: FILE_FIELD_NAME,
  label: 'Upload Pedigree Data',
  component: UploadPedigreeField,
}

const AGREE_CHECKBOX = {
  name: 'agreeSeqrAccess',
  component: BooleanCheckbox,
  label: 'By submitting this form I agree to grant seqr access to the data in the associated workspace',
}

const FORM_FIELDS = [PROJECT_DESC_FIELD, UPLOAD_PEDIGREE_FIELD, GENOME_VERSION_FIELD, AGREE_CHECKBOX]

const createProjectFromWorkspace = (values, namespace, name) => {
  if (values[FILE_FIELD_NAME]) {
    values.uploadedFileId = values[FILE_FIELD_NAME].uploadedFileId
    delete values[FILE_FIELD_NAME]
  }
  return new HttpRequestHelper(`/api/create_project_from_workspace/submit/${namespace}/${name}`,
    (responseJson) => {
      window.location.href = `/project/${responseJson.projectGuid}/project_page`
    },
    (e) => {
      if (e.body && e.body.errors) {
        throw new SubmissionError({ _error: e.body.errors })
      } else {
        throw new SubmissionError({ _error: [e.message] })
      }
    },
  ).post(values)
}

const LoadWorkspaceDataForm = React.memo(({ namespace, name }) =>
  <div>
    <Header className="large center aligned">Load data to seqr from AnVIL Workspace &quot;{namespace}/{name}&quot;</Header>
    <ReduxFormWrapper
      form="loadWorkspaceData"
      modalName="loadWorkspaceData"
      onSubmit={values => createProjectFromWorkspace(values, namespace, name)}
      confirmCloseIfNotSaved
      closeOnSuccess
      showErrorPanel
      liveValidate
      size="small"
      fields={FORM_FIELDS}
    />
  </div>,
)

LoadWorkspaceDataForm.propTypes = {
  namespace: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
}

export default LoadWorkspaceDataForm

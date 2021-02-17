import React from 'react'
import PropTypes from 'prop-types'
import { Header, Segment } from 'semantic-ui-react'

import {
  FILE_FIELD_NAME,
  PROJECT_DESC_FIELD,
  GENOME_VERSION_FIELD,
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  FILE_FORMATS,
  INDIVIDUAL_CORE_EXPORT_DATA,
  INDIVIDUAL_ID_EXPORT_DATA,
} from 'shared/utils/constants'
import BulkUploadForm from 'shared/components/form/BulkUploadForm'
import ReduxFormWrapper, { validators } from 'shared/components/form/ReduxFormWrapper'
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
  <div className="field">
    {/* eslint-disable-next-line jsx-a11y/label-has-for */}
    <label key="uploadLabel">Upload Pedigree Data</label>
    <Segment key="uploadForm">
      <BulkUploadForm
        blankExportConfig={BLANK_EXPORT}
        requiredFields={REQUIRED_FIELDS}
        optionalFields={INDIVIDUAL_CORE_EXPORT_DATA}
        uploadFormats={FILE_FORMATS}
        actionDescription="load individual data from an AnVIL workspace to a new seqr project"
        url="/api/upload_temp_file"
      />
    </Segment>
  </div>,
)

const UPLOAD_PEDIGREE_FIELD = {
  name: FILE_FIELD_NAME,
  component: UploadPedigreeField,
}

const AGREE_CHECKBOX = {
  name: 'agreeSeqrAccess',
  component: BooleanCheckbox,
  label: 'By submitting this form I agree to grant seqr access to the data in the associated workspace',
  validate: validators.required,
}

const FORM_FIELDS = [PROJECT_DESC_FIELD, UPLOAD_PEDIGREE_FIELD, GENOME_VERSION_FIELD, AGREE_CHECKBOX]

const LoadWorkspaceDataForm = React.memo(({ namespace, name }) =>
  <div>
    <Header size="large" textAlign="center">Load data to seqr from AnVIL Workspace &quot;{namespace}/{name}&quot;</Header>
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
    />
  </div>,
)

LoadWorkspaceDataForm.propTypes = {
  namespace: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
}

export default LoadWorkspaceDataForm

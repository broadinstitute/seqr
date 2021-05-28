import React from 'react'
import PropTypes from 'prop-types'
import { Header, Segment, Message } from 'semantic-ui-react'
import { SubmissionError } from 'redux-form'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

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

const VCF_DOCUMENTATION_URL = 'https://storage.googleapis.com/seqr-reference-data/seqr-vcf-info.pdf'

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

const UploadPedigreeField = React.memo(({ error }) =>
  <div className={`${error ? 'error' : ''} field`}>
    {/* eslint-disable-next-line jsx-a11y/label-has-for */}
    <label key="uploadLabel">Upload Pedigree Data</label>
    <Segment key="uploadForm" color={error ? 'red' : null}>
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

UploadPedigreeField.propTypes = {
  error: PropTypes.bool,
}

const UPLOAD_PEDIGREE_FIELD = {
  name: FILE_FIELD_NAME,
  validate: validators.required,
  component: UploadPedigreeField,
}

const AGREE_CHECKBOX = {
  name: 'agreeSeqrAccess',
  component: BooleanCheckbox,
  label: 'By submitting this form I agree to grant seqr access to the data in the associated workspace',
  validate: validators.required,
}

const DATA_BUCK_FIELD = {
  name: 'dataPath',
  label: 'Path to the Joint Called VCF',
  labelHelp: 'File path for a joint called VCF available in the workspace "Files". If the VCF is split, provide the path to the directory containing the split VCF',
  placeholder: '/path-under-Files-of-the-workspace',
  validate: validators.required,
}

const REQUIRED_GENOME_FIELD = { ...GENOME_VERSION_FIELD, validate: validators.required }

const FORM_FIELDS = [DATA_BUCK_FIELD, UPLOAD_PEDIGREE_FIELD, PROJECT_DESC_FIELD, REQUIRED_GENOME_FIELD, AGREE_CHECKBOX]

const createProjectFromWorkspace = ({ uploadedFile, ...values }, namespace, name) => {
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
  ).post({ ...values, uploadedFileId: uploadedFile.uploadedFileId })
}

const LoadWorkspaceDataForm = React.memo(({ namespace, name }) =>
  <div>
    <Header size="large" textAlign="center">
      Load data to seqr from AnVIL Workspace &quot;{namespace}/{name}&quot;
    </Header>
    <Segment basic textAlign="center">
      <Message info compact>
        In order to load your data to seqr, you must have a joint called VCF available in your workspace. For more
        information about generating and validating this file,
        see <b><a href={VCF_DOCUMENTATION_URL} target="_blank">this documentation</a></b>.
      </Message>
    </Segment>
    <ReduxFormWrapper
      form="loadWorkspaceData"
      modalName="loadWorkspaceData"
      onSubmit={values => createProjectFromWorkspace(values, namespace, name)}
      confirmCloseIfNotSaved
      closeOnSuccess
      showErrorPanel
      size="small"
      fields={FORM_FIELDS}
    />
    <p>
      Need help? please submit &nbsp;
      <a href="https://github.com/populationgenomics/seqr/issues/new?labels=bug&template=bug_report.md">GitHub Issues</a>
      , &nbsp; or &nbsp;
      <a href="mailto:seqr@populationgenomics.org.au" target="_blank">
        Email Us
      </a>
    </p>
  </div>,
)

LoadWorkspaceDataForm.propTypes = {
  namespace: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
}

export default LoadWorkspaceDataForm

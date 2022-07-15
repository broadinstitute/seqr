import React from 'react'
import PropTypes from 'prop-types'
import { Header, Segment, Message } from 'semantic-ui-react'

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
  SAMPLE_TYPE_OPTIONS,
} from 'shared/utils/constants'
import { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import BulkUploadForm from 'shared/components/form/BulkUploadForm'
import FormWizard from 'shared/components/form/FormWizard'
import { validators } from 'shared/components/form/FormHelpers'
import { BooleanCheckbox, RadioGroup } from 'shared/components/form/Inputs'

const VCF_DOCUMENTATION_URL = 'https://storage.googleapis.com/seqr-reference-data/seqr-vcf-info.pdf'

const WARNING_HEADER = 'Planned Data Loading Delay'
const WARNING_BANNER = null

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

const UploadPedigreeField = React.memo(({ name, error }) => (
  <div className={`${error ? 'error' : ''} field`}>
    <label key="uploadLabel">Upload Pedigree Data</label>
    <Segment key="uploadForm" color={error ? 'red' : null}>
      <BulkUploadForm
        name={name}
        blankExportConfig={BLANK_EXPORT}
        requiredFields={REQUIRED_FIELDS}
        optionalFields={INDIVIDUAL_CORE_EXPORT_DATA}
        uploadFormats={FILE_FORMATS}
        actionDescription="load individual data from an AnVIL workspace to a new seqr project"
        url="/api/upload_temp_file"
      />
    </Segment>
  </div>
))

UploadPedigreeField.propTypes = {
  name: PropTypes.string,
  error: PropTypes.bool,
}

const UPLOAD_PEDIGREE_FIELD = {
  name: FILE_FIELD_NAME,
  validate: validateUploadedFile,
  component: UploadPedigreeField,
}

const AGREE_CHECKBOX = {
  name: 'agreeSeqrAccess',
  component: BooleanCheckbox,
  label: 'By proceeding with seqr loading, I agree to grant seqr access to the data in this workspace',
  validate: validators.required,
}

const SAMPLE_TYPE_FIELD = {
  name: 'sampleType',
  label: 'Sample Type',
  component: RadioGroup,
  options: SAMPLE_TYPE_OPTIONS.slice(0, 2),
  validate: validators.required,
}

const DATA_BUCK_FIELD = {
  name: 'dataPath',
  label: 'Path to the Joint Called VCF',
  labelHelp: 'File path for a joint called VCF available in the workspace "Files".',
  placeholder: '/path-under-Files-of-the-workspace',
  validate: validators.required,
}

const REQUIRED_GENOME_FIELD = { ...GENOME_VERSION_FIELD, validate: validators.required }

const postWorkspaceValues = (path, formatVals) => onSuccess => ({ namespace, name, ...values }) => (
  new HttpRequestHelper(`/api/create_project_from_workspace/${namespace}/${name}/${path}`, onSuccess).post(
    formatVals ? formatVals(values) : values,
  ))

const createProjectFromWorkspace = postWorkspaceValues(
  'submit', ({ uploadedFile, ...values }) => ({ ...values, uploadedFileId: uploadedFile.uploadedFileId }),
)((responseJson) => {
  window.location.href = `/project/${responseJson.projectGuid}/project_page`
})

const addDataFromWorkspace = projectGuid => values => (
  new HttpRequestHelper(`/api/project/${projectGuid}/add_workspace_data`, (responseJson) => {
    if (responseJson.success) {
      window.location.href = `/project/${projectGuid}/project_page`
    }
  }).post({ ...values, uploadedFileId: values.uploadedFile?.uploadedFileId }))

const GRANT_ACCESS_PAGE = { fields: [AGREE_CHECKBOX], onPageSubmit: postWorkspaceValues('grant_access') }
const VALIDATE_VCF_PAGE = { fields: [DATA_BUCK_FIELD, SAMPLE_TYPE_FIELD, REQUIRED_GENOME_FIELD], onPageSubmit: postWorkspaceValues('validate_vcf') }
const ADD_DATA_VALIDATE_VCF_PAGE = { ...VALIDATE_VCF_PAGE, fields: [DATA_BUCK_FIELD] }
const UPLOAD_PED_PAGE = { fields: [PROJECT_DESC_FIELD, UPLOAD_PEDIGREE_FIELD] }
const ADD_DATA_UPLOAD_PED_PAGE = { fields: [UPLOAD_PEDIGREE_FIELD] }

const FORM_WIZARD_PAGES = [GRANT_ACCESS_PAGE, VALIDATE_VCF_PAGE, UPLOAD_PED_PAGE]
const FORM_ADD_DATA_WIZARD_PAGES = [GRANT_ACCESS_PAGE, ADD_DATA_VALIDATE_VCF_PAGE, ADD_DATA_UPLOAD_PED_PAGE]

const LoadWorkspaceDataForm = React.memo(({ params, projectGuid }) => (
  <div>
    <Header size="large" textAlign="center">
      {`Load data to seqr from AnVIL Workspace "${params.namespace}/${params.name}"`}
    </Header>
    <Segment basic textAlign="center">
      <Message info compact>
        In order to load your data to seqr, you must have a joint called VCF available in your workspace. For more
        information about generating and validating this file,
        see &nbsp;
        <b><a href={VCF_DOCUMENTATION_URL} target="_blank" rel="noreferrer">this documentation</a></b>
      </Message>
      {WARNING_BANNER ? <Message error compact header={WARNING_HEADER} content={WARNING_BANNER} /> : null}
    </Segment>
    <FormWizard
      onSubmit={projectGuid ? addDataFromWorkspace(projectGuid) : createProjectFromWorkspace}
      pages={projectGuid ? FORM_ADD_DATA_WIZARD_PAGES : FORM_WIZARD_PAGES}
      initialValues={params}
      size="small"
      noModal
    />
    <p>
      Need help? please submit &nbsp;
      <a href="https://github.com/broadinstitute/seqr/issues/new?labels=bug&template=bug_report.md">GitHub Issues</a>
      , &nbsp; or &nbsp;
      <a href="mailto:seqr@broadinstitute.org" target="_blank" rel="noreferrer">
        Email Us
      </a>
    </p>
  </div>
))

LoadWorkspaceDataForm.propTypes = {
  params: PropTypes.object.isRequired,
  projectGuid: PropTypes.string,
}

export default LoadWorkspaceDataForm

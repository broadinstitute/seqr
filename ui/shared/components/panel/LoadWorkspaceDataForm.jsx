import React from 'react'
import PropTypes from 'prop-types'
import { Header, Segment, Message } from 'semantic-ui-react'
import { connect } from 'react-redux'

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
import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import AnvilFileSelector from 'shared/components/form/AnvilFileSelector'

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
  component: AnvilFileSelector,
  validate: validators.required,
}

const REQUIRED_GENOME_FIELD = { ...GENOME_VERSION_FIELD, validate: validators.required }

const postWorkspaceValues = (path, formatVals, formatUrl) => onSuccess => (
  { workspaceNamespace, workspaceName, ...values },
) => (
  new HttpRequestHelper(
    formatUrl ? formatUrl(values) : `/api/create_project_from_workspace/${workspaceNamespace}/${workspaceName}/${path}`,
    onSuccess,
  ).post(formatVals ? formatVals(values) : values)
)

const postSubmitValues = formatUrl => postWorkspaceValues(
  'submit', ({ uploadedFile, ...values }) => ({ ...values, uploadedFileId: uploadedFile.uploadedFileId }), formatUrl,
)

const createProjectFromWorkspace = postSubmitValues()((responseJson) => {
  window.location.href = `/project/${responseJson.projectGuid}/project_page`
})

const addDataFromWorkspace = values => dispatch => postSubmitValues(
  ({ projectGuid }) => (`/api/project/${projectGuid}/add_workspace_data`),
)((responseJson) => {
  dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
})(values)

const GRANT_ACCESS_PAGE = { fields: [AGREE_CHECKBOX], onPageSubmit: postWorkspaceValues('grant_access') }
const VALIDATE_VCF_PAGE = {
  fields: [DATA_BUCK_FIELD, SAMPLE_TYPE_FIELD, REQUIRED_GENOME_FIELD],
  onPageSubmit: postWorkspaceValues('validate_vcf'),
}

const NEW_PROJECT_WIZARD_PAGES = [
  GRANT_ACCESS_PAGE,
  VALIDATE_VCF_PAGE,
  { fields: [PROJECT_DESC_FIELD, UPLOAD_PEDIGREE_FIELD] },
]

const ADD_DATA_WIZARD_PAGES = [
  GRANT_ACCESS_PAGE,
  { ...VALIDATE_VCF_PAGE, fields: [DATA_BUCK_FIELD] },
  { fields: [UPLOAD_PEDIGREE_FIELD] },
]

const LoadWorkspaceDataForm = React.memo(({ params, onAddData, ...props }) => (
  <div>
    <Header size="large" textAlign="center">
      {`Load data to seqr from AnVIL Workspace "${params.workspaceNamespace}/${params.workspaceName}"`}
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
      {...props}
      onSubmit={onAddData || createProjectFromWorkspace}
      pages={params.projectGuid ? ADD_DATA_WIZARD_PAGES : NEW_PROJECT_WIZARD_PAGES}
      initialValues={params}
      size="small"
      noModal
    />
    <p>
      Need help? please submit &nbsp;
      <a href="https://github.com/populationgenomics/seqr/issues/new?labels=bug&template=bug_report.md">GitHub Issues</a>
      , &nbsp; or &nbsp;
      <a href="mailto:seqr@populationgenomics.org.au" target="_blank" rel="noreferrer">
        Email Us
      </a>
    </p>
  </div>
))

LoadWorkspaceDataForm.propTypes = {
  params: PropTypes.object.isRequired,
  onAddData: PropTypes.func,
}

const mapDispatchToProps = {
  onAddData: addDataFromWorkspace,
}

export const AddWorkspaceDataForm = connect(null, mapDispatchToProps)(LoadWorkspaceDataForm)

export default LoadWorkspaceDataForm

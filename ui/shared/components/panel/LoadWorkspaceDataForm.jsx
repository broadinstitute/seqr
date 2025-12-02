import React from 'react'
import PropTypes from 'prop-types'
import { Header, Segment, List } from 'semantic-ui-react'
import { connect } from 'react-redux'

import {
  FILE_FIELD_NAME,
  PROJECT_DESC_FIELD,
  GENOME_VERSION_FIELD,
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  FILE_FORMATS,
  INDIVIDUAL_CORE_EXPORT_DATA,
  INDIVIDUAL_ID_EXPORT_DATA,
  INDIVIDUAL_HPO_EXPORT_DATA,
  INDIVIDUAL_FIELD_FEATURES,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
  SAMPLE_TYPE_OPTIONS,
  LoadDataVCFMessage,
} from 'shared/utils/constants'
import { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import BulkUploadForm from 'shared/components/form/BulkUploadForm'
import FormWizard from 'shared/components/form/FormWizard'
import { validators } from 'shared/components/form/FormHelpers'
import { BooleanCheckbox, RadioGroup } from 'shared/components/form/Inputs'
import PhiWarningUploadField from 'shared/components/form/PhiWarningUploadField'
import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import AnvilFileSelector from 'shared/components/form/AnvilFileSelector'

export const WORKSPACE_REQUIREMENTS = [
  '"Writer" or "Owner" level access to the workspace',
  'The "Can Share" permission enabled for the workspace',
  (
    <span>
      No &nbsp;
      <a href="https://support.terra.bio/hc/en-us/articles/360026775691" target="_blank" rel="noreferrer">
        authorization domains
      </a>
      &nbsp; to be associated with the workspace
    </span>
  ),
]

const NON_ID_REQUIRED_FIELDS = [INDIVIDUAL_FIELD_SEX, INDIVIDUAL_FIELD_AFFECTED]
const HPO_FIELD = { ...INDIVIDUAL_HPO_EXPORT_DATA[0], header: 'HPO Terms' }

const FIELD_DESCRIPTIONS = {
  [FAMILY_FIELD_ID]: 'Family ID',
  [INDIVIDUAL_FIELD_ID]: 'Individual ID (needs to match the VCF ids)',
  [INDIVIDUAL_FIELD_SEX]: 'Male, Female, or Unknown',
  [INDIVIDUAL_FIELD_AFFECTED]: 'Affected, Unaffected, or Unknown',
  [INDIVIDUAL_FIELD_FEATURES]: 'Semi-colon separated list of HPO terms. Required for affected individuals only.',
}
const REQUIRED_FIELDS = [
  ...INDIVIDUAL_ID_EXPORT_DATA,
  ...INDIVIDUAL_CORE_EXPORT_DATA.filter(({ field }) => NON_ID_REQUIRED_FIELDS.includes(field)),
  HPO_FIELD,
].map(config => ({ ...config, description: FIELD_DESCRIPTIONS[config.field] }))

const OPTIONAL_FIELDS = INDIVIDUAL_CORE_EXPORT_DATA.filter(({ field }) => !NON_ID_REQUIRED_FIELDS.includes(field))

const BLANK_EXPORT = {
  filename: 'individuals_template',
  rawData: [],
  headers: [...INDIVIDUAL_ID_EXPORT_DATA, ...INDIVIDUAL_CORE_EXPORT_DATA, HPO_FIELD].map(config => config.header),
  processRow: val => val,
}

const DEMO_EXPORT = {
  ...BLANK_EXPORT,
  filename: 'demo_individuals',
  rawData: [
    ['FAM1', 'FAM1_1', 'FAM1_2', 'FAM1_3', 'Male', 'Affected', '', 'HP:0001324 (Muscle weakness)'],
    ['FAM1', 'FAM1_4', 'FAM1_2', 'FAM1_3', '', 'Affected', 'an affected sibling', 'HP:0001250 (Seizure); HP:0001324 (Muscle weakness)'],
    ['FAM1', 'FAM1_2', '', '', 'Male', 'Unaffected', '', ''],
    ['FAM1', 'FAM1_3', '', '', 'Female', 'Unknown', 'affected status of mother unknown', ''],
    ['FAM2', 'FAM2_1', '', '', 'Female', 'Affected', 'a proband-only family', 'HP:0001263 (Global developmental delay)'],
  ],
}

const PHI_DISCALIMER = `including in any of the IDs or in the notes. PHI includes names, contact information, 
birth dates, and any other identifying information`

const UploadPedigreeField = React.memo(({ name, error }) => (
  <div className={`${error ? 'error' : ''} field`}>
    <label key="uploadLabel">Upload Pedigree Data</label>
    <Segment key="uploadForm" color={error ? 'red' : null}>
      <PhiWarningUploadField fileDescriptor="pedigree file" disclaimerDetail={PHI_DISCALIMER}>
        <BulkUploadForm
          name={name}
          blankExportConfig={BLANK_EXPORT}
          exportConfig={DEMO_EXPORT}
          templateLinkContent="an example pedigree"
          requiredFields={REQUIRED_FIELDS}
          optionalFields={OPTIONAL_FIELDS}
          uploadFormats={FILE_FORMATS}
          actionDescription="load individual data from an AnVIL workspace to a new seqr project"
          url="/api/upload_temp_file"
        />
      </PhiWarningUploadField>
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

const ACCEPT_POLICIES_CHECKBOX = {
  name: 'agreeSeqrPolicies',
  component: BooleanCheckbox,
  label: (
    <label>
      By proceeding with seqr loading, I agree that:
      <br />
      <List bulleted relaxed>
        <List.Item>
          I have read and agree to seqr’s policies documented in the &nbsp;
          <a href="/faq" target="_blank" rel="noreferrer">FAQ</a>
          , &nbsp;
          <a href="/terms_of_service" target="_blank" rel="noreferrer">Terms of Service</a>
          , &nbsp;
          and &nbsp;
          <a href="/privacy_policy" target="_blank" rel="noreferrer">Privacy Policy</a>
        </List.Item>
        <List.Item>
          The data I will load does not contain duplicate samples (i.e., the sample has not been previously loaded into
          a different project in seqr), except in cases where the previously loaded sample was an exome and this is now
          a genome, or vice versa
        </List.Item>
        <List.Item>The data I will load does not contain unrelated control samples</List.Item>
        <List.Item>
          The information I will provide such as pedigree details and HPO terms is accurate to the best of my knowledge
        </List.Item>
        <List.Item>
          Nonadherence to the stated policies or to guidance provided by the seqr team may result in permanent
          suspension of access to the platform
        </List.Item>
      </List>
    </label>
  ),
  validate: validators.required,
}

const SAMPLE_TYPE_FIELD = {
  name: 'sampleType',
  label: 'Sample Type',
  component: RadioGroup,
  options: SAMPLE_TYPE_OPTIONS,
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

const formatWorkspaceUrl = path => ({ workspaceNamespace, workspaceName }) => (
  `/api/create_project_from_workspace/${workspaceNamespace}/${workspaceName}/${path}`
)

const formatSubmitValues = ({ uploadedFile, ...values }) => ({ ...values, uploadedFileId: uploadedFile.uploadedFileId })

const onProjectCreateSuccess = (responseJson) => {
  window.location.href = `/project/${responseJson.projectGuid}/project_page`
}

const formatAddDataUrl = ({ projectGuid }) => (`/api/project/${projectGuid}/add_workspace_data`)

const onAddDataFromWorkspace = responseJson => (dispatch) => {
  dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
}

const GRANT_ACCESS_PAGE = {
  fields: [AGREE_CHECKBOX, ACCEPT_POLICIES_CHECKBOX], formatSubmitUrl: formatWorkspaceUrl('grant_access'),
}
const VALIDATE_VCF_PAGE = {
  fields: [DATA_BUCK_FIELD, SAMPLE_TYPE_FIELD, REQUIRED_GENOME_FIELD],
  formatSubmitUrl: formatWorkspaceUrl('validate_vcf'),
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

const LoadWorkspaceDataForm = React.memo(({ params, onAddData, createProject, ...props }) => (
  <div>
    <Header size="large" textAlign="center">
      {`Load data to seqr from AnVIL Workspace "${params.workspaceNamespace}/${params.workspaceName}"`}
    </Header>
    <Segment basic textAlign="center">
      <LoadDataVCFMessage isAnvil />
    </Segment>
    <FormWizard
      {...props}
      formatSubmitUrl={createProject ? formatWorkspaceUrl('submit') : formatAddDataUrl}
      onSubmitSuccess={createProject ? onProjectCreateSuccess : onAddData}
      formatSubmitValues={formatSubmitValues}
      pages={params.projectGuid ? ADD_DATA_WIZARD_PAGES : NEW_PROJECT_WIZARD_PAGES}
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
  createProject: PropTypes.bool,
  onAddData: PropTypes.func,
}

const mapDispatchToProps = {
  onAddData: onAddDataFromWorkspace,
}

export default connect(null, mapDispatchToProps)(LoadWorkspaceDataForm)

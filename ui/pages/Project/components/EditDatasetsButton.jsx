import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Message, Tab } from 'semantic-ui-react'

import Modal from 'shared/components/modal/Modal'
import { ButtonLink } from 'shared/components/StyledComponents'
import { validators } from 'shared/components/form/FormHelpers'
import FormWrapper from 'shared/components/form/FormWrapper'
import { UPLOAD_PROJECT_IGV_FIELD } from 'shared/components/form/IGVUploadField'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import { BooleanCheckbox, Select } from 'shared/components/form/Inputs'
import AddWorkspaceDataForm from 'shared/components/panel/LoadWorkspaceDataForm'
import { DATASET_TYPE_SNV_INDEL_CALLS, DATASET_TYPE_SV_CALLS, DATASET_TYPE_MITO_CALLS, LOAD_RNA_FIELDS, TISSUE_DISPLAY } from 'shared/utils/constants'

import { addVariantsDataset, addIGVDataset, uploadRnaSeq } from '../reducers'
import { getCurrentProject, getProjectGuid, getRnaSeqUploadStats } from '../selectors'

const MODAL_NAME = 'Datasets'

const ADD_VARIANT_FORM = 'variants'
const ADD_IGV_FORM = 'igv'
const ADD_RNA_FORM = 'rna'

const SUBMIT_FUNCTIONS = {
  [ADD_VARIANT_FORM]: addVariantsDataset,
  [ADD_IGV_FORM]: addIGVDataset,
  [ADD_RNA_FORM]: uploadRnaSeq,
}

const BaseUpdateDatasetForm = React.memo(({ formType, formFields, ...props }) => (
  <FormWrapper
    modalName={MODAL_NAME}
    confirmCloseIfNotSaved
    showErrorPanel
    size="small"
    fields={formFields}
    liveValidate={formType === ADD_IGV_FORM}
    {...props}
  />
))

BaseUpdateDatasetForm.propTypes = {
  formFields: PropTypes.arrayOf(PropTypes.object).isRequired,
  formType: PropTypes.string,
  initialValues: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: values => dispatch(SUBMIT_FUNCTIONS[ownProps.formType](values)),
})

const UpdateDatasetForm = connect(null, mapDispatchToProps)(BaseUpdateDatasetForm)

const UPLOAD_CALLSET_FIELDS = [
  {
    name: 'elasticsearchIndex',
    label: 'Elasticsearch Index*',
    labelHelp: 'The elasticsearch index where the callset has already been loaded.',
    validate: value => (value ? undefined : 'Specify the Elasticsearch Index where this callset has been loaded'),
  },
  {
    name: 'datasetType',
    label: 'Caller Type*',
    labelHelp: 'The caller used to generate the raw data for this index',
    component: Select,
    options: [
      { value: DATASET_TYPE_SNV_INDEL_CALLS, name: 'Haplotypecaller' },
      { value: DATASET_TYPE_SV_CALLS, name: 'SV Caller' },
      { value: DATASET_TYPE_MITO_CALLS, name: 'Mitochondria Caller' },
    ],
    validate: value => (value ? undefined : 'Specify the caller type'),
  },
  {
    name: 'mappingFilePath',
    label: 'ID Mapping File Path',
    labelHelp: 'Optional path to a file that maps VCF Sample Ids (column 1) to their corresponding Seqr Individual Ids (column 2). It can either be on the server filesystem or on Google cloud storage.',
    placeholder: 'gs:// Google bucket path or server filesystem path',
  },
  {
    name: 'ignoreExtraSamplesInCallset',
    component: BooleanCheckbox,
    label: 'Ignore extra samples in callset',
    labelHelp: 'If the callset contains sample ids that don\'t match individuals in this project, ignore them instead of reporting an error.',
  },
]

const mapStateToProps = state => ({
  url: `/api/project/${getProjectGuid(state)}/upload_igv_dataset`,
})

const UPLOAD_IGV_FIELDS = [
  {
    ...UPLOAD_PROJECT_IGV_FIELD,
    component: connect(mapStateToProps)(FileUploadField),
    required: true,
  },
]

const PROJECT_LOAD_RNA_FIELDS = [
  ...LOAD_RNA_FIELDS.slice(0, -1),
  {
    name: 'tissue',
    label: 'Tissue',
    component: Select,
    options: Object.entries(TISSUE_DISPLAY).map(([value, name]) => ({ value, name })),
    validate: validators.required,
  },
  ...LOAD_RNA_FIELDS.slice(-1),
]

const BaseRnaUpdateForm = ({ onSubmit, uploadStats }) => (
  <div>
    <BaseUpdateDatasetForm
      onSubmit={onSubmit}
      closeOnSuccess={false}
      formFields={PROJECT_LOAD_RNA_FIELDS}
    />
    {uploadStats?.info?.length > 0 && <Message info list={uploadStats.info} />}
    {uploadStats?.warnings?.length > 0 && <Message warning list={uploadStats.warnings} />}
  </div>
)

BaseRnaUpdateForm.propTypes = {
  onSubmit: PropTypes.func,
  uploadStats: PropTypes.object,
}

const mapRnaStateToProps = state => ({
  uploadStats: getRnaSeqUploadStats(state),
})

const mapRnaDispatchToProps = {
  onSubmit: uploadRnaSeq,
}

const RnaUpdateForm = connect(mapRnaStateToProps, mapRnaDispatchToProps)(BaseRnaUpdateForm)

const DEFAULT_UPLOAD_CALLSET_VALUE = { datasetType: DATASET_TYPE_SNV_INDEL_CALLS }

const ADD_RNA_DATA_PANE = {
  menuItem: 'Add RNA Data',
  render: () => (
    <Tab.Pane key="loadRna">
      <RnaUpdateForm />
    </Tab.Pane>
  ),
}

const ES_ENABLED_PANES = [...[
  {
    title: 'Upload New Callset',
    formType: ADD_VARIANT_FORM,
    formFields: UPLOAD_CALLSET_FIELDS,
    initialValues: DEFAULT_UPLOAD_CALLSET_VALUE,
  },
  {
    title: 'Add IGV Paths',
    formType: ADD_IGV_FORM,
    formFields: UPLOAD_IGV_FIELDS,
  },
].map(({ title, formType, formFields, initialValues }) => ({
  menuItem: title,
  render: () => (
    <Tab.Pane key={formType}>
      <UpdateDatasetForm
        formType={formType}
        formFields={formFields}
        initialValues={initialValues}
      />
    </Tab.Pane>
  ),
})), ADD_RNA_DATA_PANE]

const PANES = ES_ENABLED_PANES.slice(1)

const WORKSPACE_DATA_PANES = [
  {
    menuItem: 'Add VCF Data',
    render: () => (
      <Tab.Pane key="loadData">
        <AddProjectWorkspaceDataForm
          successMessage="Your request to load data has been submitted. Loading data from AnVIL to seqr is a slow process, and generally takes a week. You will receive an email letting you know once your new data is available."
        />
      </Tab.Pane>
    ),
  },
  ES_ENABLED_PANES[2],
]

const mapAddDataStateToProps = state => ({
  params: getCurrentProject(state),
})

const AddProjectWorkspaceDataForm = connect(mapAddDataStateToProps)(AddWorkspaceDataForm)

const EditDatasetsButton = React.memo(({ showLoadWorkspaceData, elasticsearchEnabled, user }) => {
  const showEditDatasets = user.isDataManager || user.isPm
  const showAddCallset = user.isDataManager && elasticsearchEnabled
  let panes = null
  if (showEditDatasets) {
    panes = showAddCallset ? ES_ENABLED_PANES : PANES
  } else if (showLoadWorkspaceData) {
    panes = WORKSPACE_DATA_PANES
  }
  return panes && (
    <Modal
      modalName={MODAL_NAME}
      title={showEditDatasets ? 'Datasets' : 'Load Additional Data From AnVIL Workspace'}
      size="small"
      trigger={<ButtonLink>{showEditDatasets ? 'Edit Datasets' : 'Load Additional Data'}</ButtonLink>}
    >
      <Tab panes={panes} />
    </Modal>
  )
})

EditDatasetsButton.propTypes = {
  showLoadWorkspaceData: PropTypes.bool,
  elasticsearchEnabled: PropTypes.bool,
  user: PropTypes.object,
}

export default EditDatasetsButton

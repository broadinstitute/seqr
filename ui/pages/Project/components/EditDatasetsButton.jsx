import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Tab } from 'semantic-ui-react'

import Modal from 'shared/components/modal/Modal'
import { ButtonLink } from 'shared/components/StyledComponents'
import FormWrapper from 'shared/components/form/FormWrapper'
import { UPLOAD_PROJECT_IGV_FIELD } from 'shared/components/form/IGVUploadField'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import { BooleanCheckbox, Select } from 'shared/components/form/Inputs'
import AddWorkspaceDataForm from 'shared/components/panel/LoadWorkspaceDataForm'
import { DATASET_TYPE_SNV_INDEL_CALLS, DATASET_TYPE_SV_CALLS, DATASET_TYPE_MITO_CALLS } from 'shared/utils/constants'

import { addVariantsDataset, addIGVDataset } from '../reducers'
import { getCurrentProject, getProjectGuid } from '../selectors'

const MODAL_NAME = 'Datasets'

const ADD_VARIANT_FORM = 'variants'
const ADD_IGV_FORM = 'igv'

const SUBMIT_FUNCTIONS = {
  [ADD_VARIANT_FORM]: addVariantsDataset,
  [ADD_IGV_FORM]: addIGVDataset,
}

const BaseUpdateDatasetForm = React.memo(({ formType, formFields, initialValues, onSubmit }) => (
  <FormWrapper
    modalName={MODAL_NAME}
    onSubmit={onSubmit}
    confirmCloseIfNotSaved
    showErrorPanel
    size="small"
    fields={formFields}
    liveValidate={formType === ADD_IGV_FORM}
    initialValues={initialValues}
  />
))

BaseUpdateDatasetForm.propTypes = {
  formFields: PropTypes.arrayOf(PropTypes.object).isRequired,
  formType: PropTypes.string.isRequired,
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

const DEFAULT_UPLOAD_CALLSET_VALUE = { datasetType: DATASET_TYPE_SNV_INDEL_CALLS }

const PANES = [
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
}))

const IGV_ONLY_PANES = [PANES[1]]

const mapAddDataStateToProps = state => ({
  params: getCurrentProject(state),
})

const AddProjectWorkspaceDataForm = connect(mapAddDataStateToProps)(AddWorkspaceDataForm)

const EditDatasetsButton = React.memo(({ showLoadWorkspaceData, elasticsearchEnabled, user }) => {
  const showEditDatasets = user.isDataManager || user.isPm
  const showAddCallset = user.isDataManager && elasticsearchEnabled
  return (
    (showEditDatasets || showLoadWorkspaceData) ? (
      <Modal
        modalName={MODAL_NAME}
        title={showEditDatasets ? 'Datasets' : 'Load Additional Data From AnVIL Workspace'}
        size="small"
        trigger={<ButtonLink>{showEditDatasets ? 'Edit Datasets' : 'Load Additional Data'}</ButtonLink>}
      >
        {showEditDatasets ? <Tab panes={showAddCallset ? PANES : IGV_ONLY_PANES} /> : (
          <AddProjectWorkspaceDataForm
            successMessage="Your request to load data has been submitted. Loading data from AnVIL to seqr is a slow process, and generally takes a week. You will receive an email letting you know once your new data is available."
          />
        )}
      </Modal>
    ) : null
  )
})

EditDatasetsButton.propTypes = {
  showLoadWorkspaceData: PropTypes.bool,
  elasticsearchEnabled: PropTypes.bool,
  user: PropTypes.object,
}

export default EditDatasetsButton

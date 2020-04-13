import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Tab } from 'semantic-ui-react'

import { getProjectGuid } from 'redux/selectors'
import Modal from 'shared/components/modal/Modal'
import { ButtonLink } from 'shared/components/StyledComponents'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import FileUploadField, { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import { BooleanCheckbox, Select } from 'shared/components/form/Inputs'
import { DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_SV_CALLS } from 'shared/utils/constants'

import { addVariantsDataset, addIGVDataset } from '../reducers'

const DropzoneLabel = styled.span`
  text-align: left;
  display: inline-block;
  margin-left: -5em;
  margin-right: -5em;
`

const UPLOADER_STYLE = { textAlign: 'left' }

const MODAL_NAME = 'Datasets'

const ADD_VARIANT_FORM = 'variants'
const ADD_IGV_FORM = 'igv'

const SUBMIT_FUNCTIONS = {
  [ADD_VARIANT_FORM]: addVariantsDataset,
  [ADD_IGV_FORM]: addIGVDataset,
}

const BaseUpdateDatasetForm = React.memo(({ formType, formFields, initialValues, onSubmit }) => (
  <ReduxFormWrapper
    form={`upload${formType}`}
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
  formFields: PropTypes.array.isRequired,
  formType: PropTypes.string.isRequired,
  initialValues: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: (values) => {
    return dispatch(SUBMIT_FUNCTIONS[ownProps.formType](values))
  },
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
      { value: DATASET_TYPE_VARIANT_CALLS, name: 'Haplotypecaller' },
      { value: DATASET_TYPE_SV_CALLS, name: 'SV Caller' },
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

const IGVFileUploadField = React.memo(({ projectGuid, ...props }) =>
  <FileUploadField
    clearTimeOut={0}
    dropzoneLabel={
      <DropzoneLabel>
        Upload a file that maps seqr Individual Ids to their BAM or CRAM file path
        <br />
        <br />
        <b>File Format:</b> Tab-separated file (.tsv) or Excel spreadsheet (.xls)<br />
        <b>Column 1:</b> Individual ID<br />
        <b>Column 2:</b> gs:// Google bucket path or server filesystem path of the BAM or CRAM file for this Individual<br />
      </DropzoneLabel>
    }
    url={`/api/project/${projectGuid}/upload_igv_dataset`}
    auto
    required
    uploaderStyle={UPLOADER_STYLE}
    {...props}
  />,
)

IGVFileUploadField.propTypes = {
  projectGuid: PropTypes.string,
}

const mapStateToProps = state => ({
  projectGuid: getProjectGuid(state),
})

const UPLOAD_IGV_FIELDS = [
  {
    name: 'mappingFile',
    component: connect(mapStateToProps)(IGVFileUploadField),
    validate: validateUploadedFile,
  },
]

const DEFAULT_UPLOAD_CALLSET_VALUE = { datasetType: DATASET_TYPE_VARIANT_CALLS }

const PANES = [
  {
    title: 'Upload New Callset',
    formType: ADD_VARIANT_FORM,
    formFields: UPLOAD_CALLSET_FIELDS,
    initialValues: DEFAULT_UPLOAD_CALLSET_VALUE,
  },
  {
    title: 'Add BAM/CRAM Paths',
    formType: ADD_IGV_FORM,
    formFields: UPLOAD_IGV_FIELDS,
  },
].map(({ title, formType, formFields, initialValues }) => ({
  menuItem: title,
  render: () =>
    <Tab.Pane key={formType}>
      <UpdateDatasetForm
        formType={formType}
        formFields={formFields}
        initialValues={initialValues}
      />
    </Tab.Pane>,
}))

export default React.memo(() => (
  <Modal
    modalName={MODAL_NAME}
    title="Datasets"
    size="small"
    trigger={<ButtonLink>Edit Datasets</ButtonLink>}
  >
    <Tab panes={PANES} />
  </Modal>
))

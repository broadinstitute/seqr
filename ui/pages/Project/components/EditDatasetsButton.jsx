import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Tab } from 'semantic-ui-react'

import { SAMPLE_TYPE_OPTIONS, DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_READ_ALIGNMENTS } from 'shared/utils/constants'
import Modal from 'shared/components/modal/Modal'
import { ButtonLink } from 'shared/components/StyledComponents'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import FileUploadField, { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import { BooleanCheckbox, Select } from 'shared/components/form/Inputs'

import { addDataset } from '../reducers'

const DropzoneLabel = styled.span`
  text-align: left;
  display: inline-block;
  margin-left: -5em;
  margin-right: -5em;
`

const MODAL_NAME = 'Datasets'

const BaseUpdateDatasetForm = ({ datasetType, formFields, onSubmit }) => (
  <ReduxFormWrapper
    form={`upload${datasetType}`}
    modalName={MODAL_NAME}
    onSubmit={onSubmit}
    confirmCloseIfNotSaved
    showErrorPanel
    size="small"
    fields={formFields}
  />
)

BaseUpdateDatasetForm.propTypes = {
  formFields: PropTypes.array.isRequired,
  datasetType: PropTypes.string.isRequired,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: (values) => {
    return dispatch(addDataset(values, ownProps.datasetType))
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

const UPLOAD_ALIGNMENT_FIELDS = [
  {
    name: 'sampleType',
    label: 'Sample Type',
    labelHelp: 'Biological sample type',
    component: Select,
    options: SAMPLE_TYPE_OPTIONS,
    validate: value => (value ? undefined : 'Specify the Sample Type'),
  },
  {
    name: 'mappingFile',
    component: FileUploadField,
    clearTimeOut: 0,
    auto: true,
    required: true,
    validate: validateUploadedFile,
    uploaderStyle: { textAlign: 'left' },
    dropzoneLabel: (
      <DropzoneLabel>
        Upload a file that maps seqr Individual Ids to their BAM or CRAM file path
        <br />
        <br />
        <b>File Format:</b> Tab-separated file (.tsv) or Excel spreadsheet (.xls)<br />
        <b>Column 1:</b> Individual ID<br />
        <b>Column 2:</b> gs:// Google bucket path or server filesystem path of the BAM or CRAM file for this Individual<br />
      </DropzoneLabel>
    ),
  },
]


const PANES = [
  {
    title: 'Upload New Callset',
    datasetType: DATASET_TYPE_VARIANT_CALLS,
    formFields: UPLOAD_CALLSET_FIELDS,
  },
  {
    title: 'Add BAM/CRAM Paths',
    datasetType: DATASET_TYPE_READ_ALIGNMENTS,
    formFields: UPLOAD_ALIGNMENT_FIELDS,
  },
].map(({ title, datasetType, formFields }) => ({
  menuItem: title,
  render: () =>
    <Tab.Pane key={datasetType}>
      <UpdateDatasetForm
        datasetType={datasetType}
        formFields={formFields}
      />
    </Tab.Pane>,
}))

export default () => (
  <Modal
    modalName={MODAL_NAME}
    title="Datasets"
    size="small"
    trigger={<ButtonLink>Edit Datasets</ButtonLink>}
  >
    <Tab panes={PANES} />
  </Modal>
)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { addDataset } from 'pages/Project/reducers'
import { SAMPLE_TYPE_OPTIONS } from '../../utils/constants'
import ReduxFormWrapper from './ReduxFormWrapper'
import FileUploadField from './XHRUploaderField'
import { BooleanCheckbox, Select } from './Inputs'

const DropzoneLabel = styled.span`
  span:first-child {
    margin-left: -5em;
    white-space: nowrap;
  }
`

export const ES_INDEX_FIELD = {
  name: 'elasticsearchIndex',
  label: 'Elasticsearch Index*',
  labelHelp: 'The elasticsearch index where the callset has already been loaded.',
  validate: value => (value ? undefined : 'Specify the Elasticsearch Index where this callset has been loaded'),
}
export const SAMPLE_TYPE_FIELD = {
  name: 'sampleType',
  label: 'Sample Type*',
  labelHelp: 'Biological sample type',
  component: Select,
  options: SAMPLE_TYPE_OPTIONS,
  validate: value => (value ? undefined : 'Specify the Sample Type'),
}
export const DATASET_NAME_FIELD = { name: 'datasetName', label: 'Name', labelHelp: 'Callset name' }
export const DATASET_PATH_FIELD = {
  name: 'datasetPath',
  label: 'Callset Path',
  labelHelp: 'Callset path either on the server filesystem or on Google cloud storage. The file can be a compressed VCF (*.vcf.gz), or a hail VDS file.',
  placeholder: 'gs:// Google bucket path or server filesystem path',
}
export const IGNORE_EXTRAS_FIELD = {
  name: 'ignoreExtraSamplesInCallset',
  component: BooleanCheckbox,
  label: 'Ignore extra samples in callset',
  labelHelp: 'If the callset contains sample ids that don\'t match individuals in this project, ignore them instead of reporting an error.',
}

export const mappingFileField = ({ required, dropzoneLabelMessage, column1Label, column2Label }) => ({
  name: 'mappingFile',
  component: FileUploadField,
  clearTimeOut: 0,
  auto: true,
  required,
  dropzoneLabel: (
    <DropzoneLabel>
      <span>{dropzoneLabelMessage}</span> <br />
      <br />
      <b>File Format:</b> Tab-separated file (.tsv) or Excel spreadsheet (.xls)<br />
      <b>Column 1:</b> {column1Label}<br />
      <b>Column 2:</b> {column2Label}<br />
    </DropzoneLabel>
  ),
})


const UpdateDatasetForm = ({ formName, modalName, datasetType, formFields, submitButtonText, addDataset: dispatchAddDataset }) => {
  const initialValues = { datasetType }
  return (
    <ReduxFormWrapper
      form={formName}
      modalName={modalName}
      onSubmit={dispatchAddDataset}
      confirmCloseIfNotSaved={false}
      showErrorPanel
      submitButtonText={submitButtonText}
      size="small"
      fields={formFields}
      initialValues={initialValues}
    />
  )
}

UpdateDatasetForm.propTypes = {
  formName: PropTypes.string.isRequired,
  formFields: PropTypes.array.isRequired,
  datasetType: PropTypes.string,
  submitButtonText: PropTypes.string,
  modalName: PropTypes.string,
  addDataset: PropTypes.func,
}

const mapDispatchToProps = { addDataset }

export default connect(null, mapDispatchToProps)(UpdateDatasetForm)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { addDataset } from 'pages/Project/reducers'
import { SAMPLE_TYPE_OPTIONS, DATASET_TYPE_READ_ALIGNMENTS } from '../../../utils/constants'
import ReduxFormWrapper from '../ReduxFormWrapper'
import FileUploadField from '../XHRUploaderField'
import { Select } from '../Inputs'

const DropzoneLabel = styled.span`
  span:first-child {
    margin-left: -5em;
    white-space: nowrap;
  }
`

const FIELDS = [
  {
    name: 'sampleType',
    label: 'Sample Type*',
    labelHelp: 'Biological sample type',
    component: Select,
    options: SAMPLE_TYPE_OPTIONS,
    validate: value => (value ? undefined : 'Specify the Sample Type'),
  },
  {
    name: 'mappingFile',
    component: FileUploadField,
    clearTimeOut: 0,
    required: true,
    dropzoneLabel: (
      <DropzoneLabel>
        <span>Upload a file that maps that maps seqr Individual Ids to their BAM or CRAM file path.</span> <br />
        <br />
        <b>File Format:</b> Tab-separated file (.tsv) or Excel spreadsheet (.xls)<br />
        <b>Column 1:</b> Individual ID<br />
        <b>Column 2:</b> gs:// Google bucket path or server filesystem path of the BAM or CRAM file for this Individual<br />
      </DropzoneLabel>
    ),
    auto: true,
  },
]


const INITIAL_DATA = { datasetType: DATASET_TYPE_READ_ALIGNMENTS }

const AddLoadedCallsetForm = ({ modalName, addDataset: dispatchAddDataset }) =>
  <ReduxFormWrapper
    form="addAlignment"
    modalName={modalName}
    onSubmit={dispatchAddDataset}
    confirmCloseIfNotSaved={false}
    showErrorPanel
    submitButtonText="Add"
    size="small"
    fields={FIELDS}
    initialValues={INITIAL_DATA}
  />

AddLoadedCallsetForm.propTypes = {
  modalName: PropTypes.string,
  addDataset: PropTypes.func,
}

const mapDispatchToProps = { addDataset }

export { AddLoadedCallsetForm as AddLoadedCallsetFormComponent }

export default connect(null, mapDispatchToProps)(AddLoadedCallsetForm)

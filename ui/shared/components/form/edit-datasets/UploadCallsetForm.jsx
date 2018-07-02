import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { addDataset } from 'pages/Project/reducers'
import ReduxFormWrapper from '../ReduxFormWrapper'
import { Select, BooleanCheckbox } from '../Inputs'

// TODO constants
const SAMPLE_TYPES = [
  { key: 'WES', value: 'WES', text: 'Exome' },
  { key: 'WGS', value: 'WGS', text: 'Genome' },
  { key: 'RNA', value: 'RNA', text: 'RNA-seq' },
]


const FIELDS = [
  {
    name: 'elasticsearchIndex',
    label: 'Elasticsearch Index*',
    labelHelp: 'The elasticsearch index where the callset has already been loaded.',
    validate: value => (value ? undefined : 'Specify the Elasticsearch Index where this callset has been loaded'),
  },
  {
    name: 'sampleType',
    label: 'Sample Type*',
    labelHelp: 'Biological sample type',
    component: Select,
    options: SAMPLE_TYPES,
    validate: value => (value ? undefined : 'Specify the Sample Type'),
  },
  { name: 'datasetName', label: 'Name', labelHelp: 'Callset name' },
  {
    name: 'datasetPath',
    label: 'Callset Path',
    labelHelp: 'Callset path either on the server filesystem or on Google cloud storage. The file can be a compressed VCF (*.vcf.gz), or a hail VDS file.',
    placeholder: 'gs:// Google bucket path or server filesystem path',
  },
  {
    name: 'ignoreExtraSamplesInCallset',
    component: BooleanCheckbox,
    label: 'Ignore extra samples in callset',
    labelHelp: 'If the callset contains sample ids that don\'t match individuals in this project, ignore them instead of reporting an error.',
  },
  {
    name: 'sampleIdsToIndividualIdsPath',
    label: 'Sample ID To Individual ID Mapping',
    labelHelp: (
      <div>
        Path of file that maps VCF Sample Ids to their corresponding seqr Individual Ids. <br />
        <br />
        <b>File Format:</b><br />
        Tab-separated text file (.tsv) or Excel spreadsheet (.xls)<br />
        <b>Column 1:</b> Sample ID <br />
        <b>Column 2:</b> Individual ID <br />
      </div>
    ),
    placeholder: 'gs:// Google bucket path or server filesystem path',
  },
]

const INITIAL_DATA = { datasetType: 'VARIANTS' }

const UploadCallsetForm = ({ modalName, addDataset: dispatchAddDataset }) =>
  <ReduxFormWrapper
    form="uploadCallset"
    modalName={modalName}
    onSubmit={dispatchAddDataset}
    confirmCloseIfNotSaved={false}
    showErrorPanel
    submitButtonText="Upload"
    size="small"
    fields={FIELDS}
    initialValues={INITIAL_DATA}
  />

UploadCallsetForm.propTypes = {
  modalName: PropTypes.string,
  addDataset: PropTypes.func,
}

const mapDispatchToProps = { addDataset }

export default connect(null, mapDispatchToProps)(UploadCallsetForm)

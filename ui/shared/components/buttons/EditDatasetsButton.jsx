import React from 'react'
import { Tab } from 'semantic-ui-react'

import { DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_READ_ALIGNMENTS } from '../../utils/constants'
import Modal from '../modal/Modal'
import UpdateDatasetForm, {
  ES_INDEX_FIELD, DATASET_NAME_FIELD, DATASET_PATH_FIELD, IGNORE_EXTRAS_FIELD, SAMPLE_TYPE_FIELD, mappingFileField,
} from '../form/UpdateDatasetForm'
import ButtonLink from './ButtonLink'


const MODAL_NAME = 'Datasets'

const UPLOAD_CALLSET_FIELDS = [
  ES_INDEX_FIELD,
  SAMPLE_TYPE_FIELD,
  DATASET_NAME_FIELD,
  DATASET_PATH_FIELD,
  IGNORE_EXTRAS_FIELD,
  mappingFileField({
    required: false,
    dropzoneLabelMessage: 'Upload an optional file that maps VCF Sample Ids to their corresponding Seqr Individual Ids',
    column1Label: 'Sample ID',
    column2Label: 'Individual ID',
  }),
]

const UPLOAD_ALIGNMENT_FIELDS = [
  SAMPLE_TYPE_FIELD,
  mappingFileField({
    required: true,
    dropzoneLabelMessage: 'Upload a file that maps that maps seqr Individual Ids to their BAM or CRAM file path',
    column1Label: 'Individual ID',
    column2Label: 'gs:// Google bucket path or server filesystem path of the BAM or CRAM file for this Individual',
  }),
]

const PANES = [
  {
    menuItem: 'Upload New Callset',
    render: () =>
      <Tab.Pane key={1}>
        <UpdateDatasetForm
          modalName={MODAL_NAME}
          formName="uploadCallset"
          datasetType={DATASET_TYPE_VARIANT_CALLS}
          formFields={UPLOAD_CALLSET_FIELDS}
          submitButtonText="Upload"
        />
      </Tab.Pane>,
  },
  {
    menuItem: 'Add BAM/CRAM Paths',
    render: () =>
      <Tab.Pane key={2}>
        <UpdateDatasetForm
          modalName={MODAL_NAME}
          formName="addAlignment"
          datasetType={DATASET_TYPE_READ_ALIGNMENTS}
          formFields={UPLOAD_ALIGNMENT_FIELDS}
          submitButtonText="Add"
        />
      </Tab.Pane>,
  },
]

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

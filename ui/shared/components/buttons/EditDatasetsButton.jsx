import React from 'react'
import { Tab } from 'semantic-ui-react'

import Modal from '../modal/Modal'
import UploadCallsetForm from '../form/edit-datasets/UploadCallsetForm'
import AddBamPathsForm from '../form/edit-datasets/AddBamPathsForm'
import ButtonLink from './ButtonLink'


const MODAL_NAME = 'Datasets'

const PANES = [
  {
    menuItem: 'Upload New Callset',
    render: () => <Tab.Pane key={1}><UploadCallsetForm modalName={MODAL_NAME} /></Tab.Pane>,
  },
  {
    menuItem: 'Add BAM/CRAM Paths',
    render: () => <Tab.Pane key={2}><AddBamPathsForm modalName={MODAL_NAME} /></Tab.Pane>,
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

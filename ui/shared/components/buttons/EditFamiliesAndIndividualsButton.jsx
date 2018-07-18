import React from 'react'
import { Tab } from 'semantic-ui-react'
import styled from 'styled-components'
import Modal from '../modal/Modal'
import EditIndividualsBulkForm from '../form/edit-families-and-individuals/EditIndividualsBulkForm'
import EditIndividualsForm from '../form/edit-families-and-individuals/EditIndividualsForm'
import EditFamiliesForm from '../form/edit-families-and-individuals/EditFamiliesForm'

const TabPane = styled(Tab.Pane)`
  padding: 1em 0 !important;
`

const MODAL_NAME = 'editFamiliesAndIndividuals'
const PANES = [
  {
    menuItem: 'Edit Families',
    pane: <TabPane key={1}><EditFamiliesForm modalName={MODAL_NAME} /></TabPane>,
  },
  {
    menuItem: 'Edit Individuals',
    pane: <TabPane key={2}><EditIndividualsForm modalName={MODAL_NAME} /></TabPane>,
  },
  {
    menuItem: 'Bulk Upload',
    pane: <TabPane key={3}><EditIndividualsBulkForm modalName={MODAL_NAME} /></TabPane>,
  },
]

export default () => (
  <Modal
    modalName={MODAL_NAME}
    title="Edit Families & Individuals"
    size="large"
    trigger={
      <div style={{ display: 'inline-block' }}>
        <a role="button" tabIndex="0" style={{ cursor: 'pointer' }}>
          Edit Families & Individuals
        </a>
      </div>
    }
  >
    <Tab
      renderActiveOnly={false}
      panes={PANES}
    />
  </Modal>

)


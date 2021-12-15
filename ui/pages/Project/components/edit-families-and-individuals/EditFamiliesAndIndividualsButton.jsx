import React from 'react'
import { Tab } from 'semantic-ui-react'
import styled from 'styled-components'
import Modal from 'shared/components/modal/Modal'
import { ButtonLink } from 'shared/components/StyledComponents'
import { EditFamiliesBulkForm, EditIndividualsBulkForm, EditIndividualMetadataBulkForm } from './BulkEditForm'
import EditIndividualsForm from './EditIndividualsForm'
import EditFamiliesForm from './EditFamiliesForm'

const TabPane = styled(Tab.Pane)`
  padding: 1em 0 !important;
`

const MODAL_NAME = 'editFamiliesAndIndividuals'
const PANE_DETAILS = [
  {
    menuItem: 'Edit Families',
    formClass: EditFamiliesForm,
  },
  {
    menuItem: 'Edit Individuals',
    formClass: EditIndividualsForm,
  },
  {
    menuItem: 'Bulk Edit Families',
    formClass: EditFamiliesBulkForm,
  },
  {
    menuItem: 'Bulk Edit Individuals',
    formClass: EditIndividualsBulkForm,
  },
  {
    menuItem: 'Bulk Edit Individual Metadata',
    formClass: EditIndividualMetadataBulkForm,
  },
]
const PANES = PANE_DETAILS.map(({ formClass, menuItem }) => ({
  render: () => <TabPane key={menuItem}>{React.createElement(formClass, { modalName: MODAL_NAME })}</TabPane>,
  menuItem,
}))

export default React.memo(() => (
  <Modal
    modalName={MODAL_NAME}
    title="Edit Families & Individuals"
    size="large"
    trigger={<ButtonLink>Edit Families & Individuals</ButtonLink>}
  >
    <Tab panes={PANES} />
  </Modal>

))

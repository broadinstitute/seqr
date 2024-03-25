import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Tab } from 'semantic-ui-react'
import styled from 'styled-components'
import Modal from 'shared/components/modal/Modal'
import { ButtonLink } from 'shared/components/StyledComponents'
import { GREGOR_FINDING_TAG_NAME } from 'shared/utils/constants'
import { EditFamiliesBulkForm, EditIndividualsBulkForm, EditIndividualMetadataBulkForm } from './BulkEditForm'
import EditIndividualsForm from './EditIndividualsForm'
import EditFamiliesForm from './EditFamiliesForm'
import ImportGregorMetadata from './ImportGregorMetadata'
import { getCurrentProject } from '../../selectors'

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
const formatPane = ({ formClass, menuItem }) => ({
  render: () => <TabPane key={menuItem}>{React.createElement(formClass, { modalName: MODAL_NAME })}</TabPane>,
  menuItem,
})
const PANES = PANE_DETAILS.map(formatPane)
const GREGOR_METADATA_PANES = [
  ...PANES,
  formatPane({ menuItem: 'Import From Gregor Metadata', formClass: ImportGregorMetadata }),
]

const EditButton = React.memo(({ hasGregorFindingTag }) => (
  <Modal
    modalName={MODAL_NAME}
    title="Edit Families & Individuals"
    size="large"
    trigger={<ButtonLink>Edit Families & Individuals</ButtonLink>}
  >
    <Tab panes={hasGregorFindingTag ? GREGOR_METADATA_PANES : PANES} />
  </Modal>
))

EditButton.propTypes = {
  hasGregorFindingTag: PropTypes.bool,
}

const mapStateToProps = state => ({
  hasGregorFindingTag: (getCurrentProject(state) || {}).variantTagTypes?.some(
    ({ name }) => name === GREGOR_FINDING_TAG_NAME,
  ),
})

export default connect(mapStateToProps)(EditButton)

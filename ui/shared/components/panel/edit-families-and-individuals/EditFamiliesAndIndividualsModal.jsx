import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Tab } from 'semantic-ui-react'
import styled from 'styled-components'

import EditIndividualsBulkForm from 'shared/components/panel/edit-families-and-individuals/EditIndividualsBulkForm'
import EditIndividualsForm from 'shared/components/panel/edit-families-and-individuals/EditIndividualsForm'
import EditFamiliesForm from 'shared/components/panel/edit-families-and-individuals/EditFamiliesForm'
import Modal from 'shared/components/modal/Modal'

import {
  getEditFamiliesAndIndividualsModalIsVisible,
  hideEditFamiliesAndIndividualsModal,
} from './EditFamiliesAndIndividualsModal-redux'


const TabPane = styled(Tab.Pane)`
  padding: 1em 0 !important;
`

class EditFamiliesAndIndividualsModal extends React.Component
{
  static propTypes = {
    isVisible: PropTypes.bool.isRequired,
    hideModal: PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.isVisible) {
      return null
    }

    return (
      <Modal
        title="Edit Families & Individuals"
        handleClose={this.handleClose}
        size="large"
      >
        <Tab
          renderActiveOnly={false}
          panes={[
            {
              menuItem: 'Edit Families',
              pane: <TabPane key={1}><EditFamiliesForm onClose={this.hideModal} /></TabPane>,
            },
            {
              menuItem: 'Edit Individuals',
              pane: <TabPane key={2}><EditIndividualsForm onClose={this.hideModal} /></TabPane>,
            },
            {
              menuItem: 'Bulk Upload',
              pane: <TabPane key={3}><EditIndividualsBulkForm onClose={this.handleCloseBulkEditForm} /></TabPane>,
            },
          ]}
        />
      </Modal>)
  }

  hideModal = () => {
    this.props.hideModal()
  }

  handleCloseBulkEditForm = () => {
    this.hideModal()
    window.location.reload() //TODO update state without refreshing
  }
}

export { EditFamiliesAndIndividualsModal as EditFamiliesAndIndividualsModalComponent }

const mapStateToProps = state => ({
  isVisible: getEditFamiliesAndIndividualsModalIsVisible(state),
})

const mapDispatchToProps = {
  hideModal: hideEditFamiliesAndIndividualsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditFamiliesAndIndividualsModal)

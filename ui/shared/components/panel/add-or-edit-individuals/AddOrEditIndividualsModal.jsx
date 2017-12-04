import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Tab } from 'semantic-ui-react'

import AddOrEditIndividualsBulkForm from 'shared/components/panel/add-or-edit-individuals/AddOrEditIndividualsBulkForm'
import EditIndividualsForm from 'shared/components/panel/add-or-edit-individuals/EditIndividualsForm'
import Modal from 'shared/components/modal/Modal'

import {
  getAddOrEditIndividualsModalIsVisible,
  hideAddOrEditIndividualsModal,
} from './state'

class AddOrEditIndividualsModal extends React.PureComponent
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
        title="Individuals"
        handleClose={this.handleClose}
        size="large"
      >
        <Tab
          panes={[
            {
              menuItem: 'Bulk Upload',
              pane: <Tab.Pane key={2}><AddOrEditIndividualsBulkForm handleClose={this.handleClose} /></Tab.Pane>,
            },
            {
              menuItem: 'Edit',
              pane: <Tab.Pane key={1}><EditIndividualsForm handleClose={this.handleClose} /></Tab.Pane>,
            },
            {
              menuItem: 'Delete',
              pane: <Tab.Pane key={3}>Delete</Tab.Pane>,
            },
          ]}
          renderActiveOnly={false}
        />
      </Modal>)
  }

  handleClose = () => {
    this.props.hideModal()
  }
}

export { AddOrEditIndividualsModal as AddOrEditIndividualsModalComponent }

const mapStateToProps = state => ({
  isVisible: getAddOrEditIndividualsModalIsVisible(state),
})

const mapDispatchToProps = {
  hideModal: hideAddOrEditIndividualsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(AddOrEditIndividualsModal)

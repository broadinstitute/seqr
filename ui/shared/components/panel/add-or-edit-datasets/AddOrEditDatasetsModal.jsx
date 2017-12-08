import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Tab } from 'semantic-ui-react'

import AddLoadedCallsetForm from 'shared/components/panel/add-or-edit-datasets/AddLoadedCallsetForm'
import UploadCallsetForm from 'shared/components/panel/add-or-edit-datasets/UploadCallsetForm'
import AddBamPathsForm from 'shared/components/panel/add-or-edit-datasets/AddBamPathsForm'
import Modal from 'shared/components/modal/Modal'

import {
  getAddOrEditDatasetsModalIsVisible,
  hideAddOrEditDatasetsModal,
} from './state'

class AddOrEditDatasetsModal extends React.PureComponent
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
        title="Datasets"
        handleClose={this.handleClose}
        size="small"
      >
        <Tab
          panes={[
            {
              menuItem: 'Add Loaded Callset',
              render: () => <Tab.Pane key={1}><AddLoadedCallsetForm handleClose={this.handleClose} /></Tab.Pane>,
            },
            {
              menuItem: 'Upload New Callset',
              render: () => <Tab.Pane key={1}><UploadCallsetForm handleClose={this.handleClose} /></Tab.Pane>,
            },
            {
              menuItem: 'Add BAM/CRAM Paths',
              render: () => <Tab.Pane key={1}><AddBamPathsForm handleClose={this.handleClose} /></Tab.Pane>,
            },
          ]}
        />
      </Modal>)
  }

  handleClose = () => {
    this.props.hideModal()
  }
}

export { AddOrEditDatasetsModal as AddOrEditDatasetsModalComponent }

const mapStateToProps = state => ({
  isVisible: getAddOrEditDatasetsModalIsVisible(state),
})

const mapDispatchToProps = {
  hideModal: hideAddOrEditDatasetsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(AddOrEditDatasetsModal)

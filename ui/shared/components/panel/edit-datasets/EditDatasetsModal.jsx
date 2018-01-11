import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Tab } from 'semantic-ui-react'

import UploadCallsetForm from 'shared/components/panel/edit-datasets/UploadCallsetForm'
import AddBamPathsForm from 'shared/components/panel/edit-datasets/AddBamPathsForm'
import Modal from 'shared/components/modal/Modal'

import {
  getEditDatasetsModalIsVisible,
  hideEditDatasetsModal,
} from './EditDatasetsModal-redux'

class EditDatasetsModal extends React.PureComponent
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
          renderActiveOnly={false}
          panes={[
            {
              menuItem: 'Upload New Callset',
              pane: <Tab.Pane key={1}><UploadCallsetForm handleClose={this.handleClose} /></Tab.Pane>,
            },
            {
              menuItem: 'Add BAM/CRAM Paths',
              pane: <Tab.Pane key={2}><AddBamPathsForm handleClose={this.handleClose} /></Tab.Pane>,
            },
          ]}
        />
      </Modal>)
  }

  handleClose = () => {
    this.props.hideModal()
  }
}

export { EditDatasetsModal as EditDatasetsModalComponent }

const mapStateToProps = state => ({
  isVisible: getEditDatasetsModalIsVisible(state),
})

const mapDispatchToProps = {
  hideModal: hideEditDatasetsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditDatasetsModal)

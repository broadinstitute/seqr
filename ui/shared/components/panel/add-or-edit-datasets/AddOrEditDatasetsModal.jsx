import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import AddDatasetForm from 'shared/components/panel/add-or-edit-datasets/AddDatasetForm'
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
        title="Add Dataset"
        handleClose={this.handleClose}
        size="small"
      >
        <AddDatasetForm handleClose={this.handleClose} />
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

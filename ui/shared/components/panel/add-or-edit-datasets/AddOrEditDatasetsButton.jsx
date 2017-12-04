import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { showAddOrEditDatasetsModal } from './state'

const AddOrEditDatasetsButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      <a
        role="button"
        tabIndex="0"
        onClick={() => props.showAddOrEditDatasetsModal()}
        style={{ cursor: 'pointer' }}
      >
        Edit Datasets
      </a>
    }
  </div>
)

AddOrEditDatasetsButton.propTypes = {
  showAddOrEditDatasetsModal: PropTypes.func.isRequired,
}

export { AddOrEditDatasetsButton as AddOrEditDatasetsButtonComponent }

const mapDispatchToProps = {
  showAddOrEditDatasetsModal,
}

export default connect(null, mapDispatchToProps)(AddOrEditDatasetsButton)


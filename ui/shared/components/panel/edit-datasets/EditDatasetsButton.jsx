import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { showEditDatasetsModal } from './EditDatasetsModal-redux'

const EditDatasetsButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      <a
        role="button"
        tabIndex="0"
        onClick={() => props.showEditDatasetsModal()}
        style={{ cursor: 'pointer' }}
      >
        Edit Datasets
      </a>
    }
  </div>
)

EditDatasetsButton.propTypes = {
  showEditDatasetsModal: PropTypes.func.isRequired,
}

export { EditDatasetsButton as EditDatasetsButtonComponent }

const mapDispatchToProps = {
  showEditDatasetsModal,
}

export default connect(null, mapDispatchToProps)(EditDatasetsButton)


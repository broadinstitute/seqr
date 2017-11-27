import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { showAddOrEditIndividualsModal } from './state'

const AddOrEditIndividualsButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      <a
        role="button"
        tabIndex="0"
        onClick={() => props.showAddOrEditIndividualsModal()}
        style={{ cursor: 'pointer' }}
      >
        Edit Individuals
      </a>
    }
  </div>
)

AddOrEditIndividualsButton.propTypes = {
  showAddOrEditIndividualsModal: PropTypes.func.isRequired,
}

export { AddOrEditIndividualsButton as AddOrEditIndividualsButtonComponent }

const mapDispatchToProps = {
  showAddOrEditIndividualsModal,
}

export default connect(null, mapDispatchToProps)(AddOrEditIndividualsButton)


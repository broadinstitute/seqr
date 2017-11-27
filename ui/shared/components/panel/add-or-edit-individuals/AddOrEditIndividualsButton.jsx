import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { showAddOrEditIndividualsModal } from './state'

const ShowAddOrEditIndividualsModalButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      <a
        role="button"
        tabIndex="0"
        onClick={() => props.showAddOrEditIndividualsModal()}
        style={{ cursor: 'pointer' }}
      >
        Add or Edit Individuals
      </a>
    }
  </div>
)

ShowAddOrEditIndividualsModalButton.propTypes = {
  showAddOrEditIndividualsModal: PropTypes.func.isRequired,
}

export { ShowAddOrEditIndividualsModalButton as ShowAddOrEditIndividualsModalButtonComponent }

const mapDispatchToProps = {
  showAddOrEditIndividualsModal,
}

export default connect(null, mapDispatchToProps)(ShowAddOrEditIndividualsModalButton)


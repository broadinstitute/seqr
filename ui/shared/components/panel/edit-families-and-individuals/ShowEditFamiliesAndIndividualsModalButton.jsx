import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { showEditFamiliesAndIndividualsModal } from './state'

const ShowEditFamiliesAndIndividualsModalButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      <a
        tabIndex="0"
        onClick={() => props.showEditFamiliesAndIndividualsModal()}
        style={{ cursor: 'pointer' }}
      >
        Edit Families and Individuals
      </a>
    }
  </div>
)

ShowEditFamiliesAndIndividualsModalButton.propTypes = {
  showEditFamiliesAndIndividualsModal: PropTypes.func.isRequired,
}

export { ShowEditFamiliesAndIndividualsModalButton as ShowEditFamiliesAndIndividualsModalButtonComponent }

const mapDispatchToProps = {
  showEditFamiliesAndIndividualsModal,
}

export default connect(null, mapDispatchToProps)(ShowEditFamiliesAndIndividualsModalButton)


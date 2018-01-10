import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { showEditFamiliesAndIndividualsModal } from './EditFamiliesAndIndividualsModal-redux'

const EditFamiliesAndIndividualsButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      <a
        role="button"
        tabIndex="0"
        onClick={() => props.showEditFamiliesAndIndividualsModal()}
        style={{ cursor: 'pointer' }}
      >
        Edit Families & Individuals
      </a>
    }
  </div>
)

EditFamiliesAndIndividualsButton.propTypes = {
  showEditFamiliesAndIndividualsModal: PropTypes.func.isRequired,
}

export { EditFamiliesAndIndividualsButton as EditFamiliesAndIndividualsButtonComponent }

const mapDispatchToProps = {
  showEditFamiliesAndIndividualsModal,
}

export default connect(null, mapDispatchToProps)(EditFamiliesAndIndividualsButton)


import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { showPedigreeImageZoomModal } from './zoom-modal/state'


const PedigreeImagePanel = props => (
  props.family.pedigreeImage ?
    <a role="button" tabIndex="0" onClick={() => props.showPedigreeImageZoomModal(props.family)}>
      <img
        src={props.family.pedigreeImage}
        alt="pedigree"
        style={{ maxHeight: '100px', maxWidth: '150px', verticalAlign: 'top', cursor: 'zoom-in' }}
      />
    </a>
    : null
)

export { PedigreeImagePanel as PedigreeImageComponent }

PedigreeImagePanel.propTypes = {
  family: PropTypes.object.isRequired,
  showPedigreeImageZoomModal: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  showPedigreeImageZoomModal,
}

export default connect(null, mapDispatchToProps)(PedigreeImagePanel)

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { showPedigreeImageZoomModal } from 'shared/components/panel/pedigree-image-zoom-modal/state'


const PedigreeImagePanel = props => (
  props.family.pedigreeImage ?
    <a tabIndex="0" onClick={() => props.showPedigreeImageZoomModal(props.family)}>
      <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '100px', maxWidth: '150px', verticalAlign: 'top', cursor: 'zoom-in' }} />
    </a>
    : null
)

export { PedigreeImagePanel as PedigreeImageComponent }

PedigreeImagePanel.propTypes = {
  family: PropTypes.object.isRequired,
  showPedigreeImageZoomModal: PropTypes.func.isRequired,
}

const mapDispatchToProps = dispatch => bindActionCreators({ showPedigreeImageZoomModal }, dispatch)

export default connect(null, mapDispatchToProps)(PedigreeImagePanel)

import React from 'react'
import PropTypes from 'prop-types'

import { Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import Modal from 'shared/components/modal/Modal'

import { getPedigreeImageZoomModalIsVisible, getPedigreeImageZoomModalFamily, hidePedigreeImageZoomModal } from './state'


const PedigreeImageZoomModal = props => (
  props.isVisible ?
    <Modal title={`Family ${props.family.displayName}`} onClose={props.hidePedigreeImageZoomModal}>
      <center>
        <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} /><br />
        <a href={props.family.pedigreeImage} target="_blank" rel="noopener noreferrer">
          <Icon name="zoom" /> Original Size
        </a>
      </center>
    </Modal> : null
)

PedigreeImageZoomModal.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  family: PropTypes.object,
  hidePedigreeImageZoomModal: PropTypes.func.isRequired,
}

export { PedigreeImageZoomModal as PedigreeImageZoomModalComponent }

const mapStateToProps = state => ({
  isVisible: getPedigreeImageZoomModalIsVisible(state),
  family: getPedigreeImageZoomModalFamily(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ hidePedigreeImageZoomModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(PedigreeImageZoomModal)

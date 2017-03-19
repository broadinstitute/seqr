import React from 'react'
import { Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import Modal from 'shared/components/Modal'


import {
  getPedigreeZoomModalIsVisible,
  getPedigreeZoomModalFamily,
  hidePedigreeZoomModal,
} from '../../../reducers/rootReducer'

const PedigreeZoomModal = props => (
  props.isVisible ?
    <Modal title={`Family ${props.family.displayName}`} onClose={props.hidePedigreeZoomModal}>
      <center>
        <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} /><br />
        <a href={props.family.pedigreeImage} target="_blank" rel="noopener noreferrer">
          <Icon name="zoom" /> Original Size
        </a>
      </center>
    </Modal> : null
)

PedigreeZoomModal.propTypes = {
  isVisible: React.PropTypes.bool.isRequired,
  family: React.PropTypes.object,
  hidePedigreeZoomModal: React.PropTypes.func.isRequired,
}

export { PedigreeZoomModal as PedigreeZoomModalComponent }

const mapStateToProps = state => ({
  isVisible: getPedigreeZoomModalIsVisible(state),
  family: getPedigreeZoomModalFamily(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ hidePedigreeZoomModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(PedigreeZoomModal)

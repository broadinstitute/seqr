import React from 'react'
//import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { showPedigreeZoomModal } from '../../../reducers/rootReducer'


const PedigreeImage = props => (
  props.family.pedigreeImage ?
    <a tabIndex="0" onClick={() => props.showPedigreeZoomModal(props.family)}>
      <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '100px', maxWidth: '150px', verticalAlign: 'top', cursor: 'zoom-in' }} />
    </a>
    : null
)

export { PedigreeImage as PedigreeImageComponent }

PedigreeImage.propTypes = {
  family: React.PropTypes.object.isRequired,
  showPedigreeZoomModal: React.PropTypes.func.isRequired,
}

const mapDispatchToProps = dispatch => bindActionCreators({ showPedigreeZoomModal }, dispatch)

export default connect(null, mapDispatchToProps)(PedigreeImage)


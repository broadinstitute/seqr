import React from 'react'
//import { Grid } from 'semantic-ui-react'
//import { connect } from 'react-redux'
//import { bindActionCreators } from 'redux'


const NewComponent = props =>
  <div>{props}</div>

NewComponent.propTypes = {
  //family: PropTypes.object.isRequired,
  //onClose: PropTypes.func.isRequired,
}

export default NewComponent

/*
const mapStateToProps = state => ({ showCategories: state.projectsTableState.showCategories })

const mapDispatchToProps = dispatch => bindActionCreators({
  onChange: null,
}, dispatch)


export default connect(mapStateToProps, mapDispatchToProps)(NewComponent)
*/

/** This is an example Component skeleton */

import React from 'react'
//import { Grid } from 'semantic-ui-react'
//import { connect } from 'react-redux'

const NewComponent = props =>
  <div>{props}</div>

NewComponent.propTypes = {
  //family: PropTypes.object.isRequired,
  //handleClose: PropTypes.func.isRequired,
}

export default NewComponent

/*
const mapStateToProps = state => ({ showCategories: state.projectsTableState.showCategories })

const mapDispatchToProps = dispatch => bindActionCreators({
  onChange: null,
}, dispatch)


export default connect(mapStateToProps, mapDispatchToProps)(NewComponent)
*/

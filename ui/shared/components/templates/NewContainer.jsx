import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

const NewContainer = props =>
  <span>{props}</span>

NewContainer.propTypes = {
  //showCategories: React.PropTypes.bool.isRequired,
  //onChange: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ showCategories: state.projectsTableState.showCategories })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: null }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(NewContainer)

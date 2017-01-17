import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { HorizontalOnOffToggle } from '../../../shared/components/form/Toggle'
import { updateShowCategories } from '../reducers/projectsTableReducer'

const ShowCategoriesToggle = props =>
  <span>
    <b>Categories:</b> &nbsp; &nbsp;
    <HorizontalOnOffToggle
      color="#4183c4"
      isOn={props.showCategories}
      onClick={() => props.onChange(!props.showCategories)}
    />
  </span>

ShowCategoriesToggle.propTypes = {
  showCategories: React.PropTypes.bool.isRequired,
  onChange: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ showCategories: state.projectsTable.showCategories })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateShowCategories }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ShowCategoriesToggle)

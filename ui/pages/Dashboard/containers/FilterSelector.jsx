import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import FilterSelector from '../components/FilterSelector'
import { updateFilter } from '../reducers/projectsTableReducer'


const mapStateToProps = state => ({ filter: state.projectsTable.filter })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateFilter }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(FilterSelector)

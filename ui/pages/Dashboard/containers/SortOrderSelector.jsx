import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import SortOrderSelector from '../components/SortOrderSelector'
import { updateSortOrder } from '../reducers/projectsTableReducer'


const mapStateToProps = state => ({ sortOrder: state.projectsTable.sortOrder })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateSortOrder }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(SortOrderSelector)

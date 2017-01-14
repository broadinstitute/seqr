import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import SortDirectionSelector from '../components/SortDirectionSelector'
import { updateSortDirection } from '../reducers/projectsTableReducer'


const mapStateToProps = state => ({ sortDirection: state.projectsTable.sortDirection })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateSortDirection }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(SortDirectionSelector)

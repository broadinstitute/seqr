import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import ShowDetailsSelector from '../components/ShowDetailsSelector'
import { updateShowDetails } from '../reducers/projectsTableReducer'

const mapStateToProps = state => ({ showDetails: state.projectsTable.showDetails })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateShowDetails }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ShowDetailsSelector)

import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { getUser } from 'shared/utils/redux/commonDataActionsAndSelectors'


const ShowIfEditPermissions = props => (
  props.user.hasEditPermissions ? props.children : null
)

ShowIfEditPermissions.propTypes = {
  user: PropTypes.object.isRequired,
  children: PropTypes.any,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(ShowIfEditPermissions)

import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { getUser } from 'redux/rootReducer'


const ShowIfStaff = props => (
  props.user.is_staff ? props.children : null
)

ShowIfStaff.propTypes = {
  user: PropTypes.object.isRequired,
  children: PropTypes.any,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(ShowIfStaff)

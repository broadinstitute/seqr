import { connect } from 'react-redux'

import BaseLayout from '../../../shared/components/BaseLayout'

const mapStateToProps = ({ user }) => ({ user })

export default connect(mapStateToProps)(BaseLayout)

import { connect } from 'react-redux'

import BaseLayout from 'shared/components/page/BaseLayout'

const mapStateToProps = ({ user }) => ({ user })

export default connect(mapStateToProps)(BaseLayout)

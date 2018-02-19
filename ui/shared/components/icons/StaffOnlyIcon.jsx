import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

const StaffOnlyIcon = props => <Popup
  trigger={<Icon name="lock" />}
  position="top center"
  size="small"
  content={props.mouseOverText || 'Only visible to internal staff users.'}
/>

StaffOnlyIcon.propTypes = {
  mouseOverText: PropTypes.string,
}

export default StaffOnlyIcon

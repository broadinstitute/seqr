import React from 'react'
import { Icon, Popup } from 'semantic-ui-react'

const StaffOnlyIcon = props => <Popup
  trigger={<Icon name="lock" />}
  positioning="top center"
  size="small"
  content={props.mouseOverText || 'Only visible to internal staff users.'}
/>

StaffOnlyIcon.propTypes = {
  mouseOverText: React.PropTypes.string,
}

export default StaffOnlyIcon

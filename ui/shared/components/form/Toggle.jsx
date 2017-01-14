import React from 'react'
import { Icon } from 'semantic-ui-react'

const linkStyle = {  /* prevent text selection on click */
  WebkitUserSelect: 'none', /* webkit (safari, chrome) browsers */
  MozUserSelect: 'none', /* mozilla browsers */
  KhtmlUserSelect: 'none', /* webkit (konqueror) browsers */
  MsUserSelect: 'none', /* IE10+ */
  verticalAlign: 'bottom',
}

const Toggle = props =>
  <a
    tabIndex="0"
    onClick={props.onClick}
    ref={(ref) => { if (ref) ref.blur() }}
    style={linkStyle}
  >
    {props.isOn ?
      <Icon size="large" style={{ cursor: 'pointer', color: props.color || '#BBBBBB' }} name="toggle on" /> :
      <Icon size="large" style={{ cursor: 'pointer', color: '#BBBBBB' }} name="toggle off" />
    }
  </a>

Toggle.propTypes = {
  onClick: React.PropTypes.func.isRequired,
  isOn: React.PropTypes.bool.isRequired,
  color: React.PropTypes.string,
}


export default Toggle

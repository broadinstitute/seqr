import React from 'react'
import { Icon } from 'semantic-ui-react'

const toggleStyle = {  /* prevent text selection on click */
  WebkitUserSelect: 'none', /* webkit (safari, chrome) browsers */
  MozUserSelect: 'none', /* mozilla browsers */
  KhtmlUserSelect: 'none', /* webkit (konqueror) browsers */
  MsUserSelect: 'none', /* IE10+ */

  verticalAlign: 'bottom',
  cursor: 'pointer',
}

//const refBlurHandler = (ref) => { if (ref) ref.blur() }

export const HorizontalOnOffToggle = props =>
  <a
    tabIndex="0"
    onClick={props.onClick}
    style={toggleStyle}
  >
    {props.isOn ?
      <Icon size="large" style={{ color: props.color || '#BBBBBB' }} name="toggle on" /> :
      <Icon size="large" style={{ color: '#BBBBBB' }} name="toggle off" />
    }
  </a>

HorizontalOnOffToggle.propTypes = {
  onClick: React.PropTypes.func.isRequired,
  isOn: React.PropTypes.bool.isRequired,
  color: React.PropTypes.string,
}


export const SortDirectionToggle = props =>
  <a
    tabIndex="0"
    onClick={props.onClick}
    style={{ ...toggleStyle, color: '#555555' }}
  >
    {props.isPointingDown ?
      <Icon name="arrow circle down" /> :  /* arrow circle down */
      <Icon name="arrow circle up" />      /* arrow circle up */
    }
  </a>

SortDirectionToggle.propTypes = {
  onClick: React.PropTypes.func.isRequired,
  isPointingDown: React.PropTypes.bool.isRequired,
}

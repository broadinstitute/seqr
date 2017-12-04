import React from 'react'
import PropTypes from 'prop-types'

import { Icon } from 'semantic-ui-react'

const HorizontalOnOffToggle = props =>
  <a
    role="button"
    tabIndex="0"
    onClick={props.onClick}
    className="clickable"
    style={{ verticalAlign: 'bottom' }}
  >
    {props.isOn ?
      <Icon size="large" style={{ color: props.color || '#BBBBBB' }} name="toggle on" /> :
      <Icon size="large" style={{ color: '#BBBBBB' }} name="toggle off" />
    }
  </a>

HorizontalOnOffToggle.propTypes = {
  onClick: PropTypes.func.isRequired,
  isOn: PropTypes.bool,
  color: PropTypes.string,
}

export default HorizontalOnOffToggle

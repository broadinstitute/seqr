import React from 'react'
import { Icon } from 'semantic-ui-react'

const VerticalArrowToggle = props =>
  <a
    tabIndex="0"
    onClick={props.onClick}
    className="clickable"
    style={{ verticalAlign: 'bottom', color: props.color || '#555555' }}
  >
    {props.isPointingDown ?
      <Icon name="arrow circle down" /> :  /* arrow circle down */
      <Icon name="arrow circle up" />      /* arrow circle up */
    }
  </a>

VerticalArrowToggle.propTypes = {
  onClick: React.PropTypes.func.isRequired,
  isPointingDown: React.PropTypes.bool,
  color: React.PropTypes.string,
}

export default VerticalArrowToggle

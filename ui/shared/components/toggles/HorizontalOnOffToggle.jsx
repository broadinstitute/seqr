import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

const Toggle = styled.a.attrs({ role: 'button', tabIndex: '0' })`
  -webkit-user-select: none;
  -moz-user-select: none;
  -khtml-user-select: none;
  -ms-user-select: none;
  cursor: pointer;
  outline: none;
  vertical-align: bottom;
`

const ToggleIcon = styled(Icon)`
  color: ${props => props.color || '#BBBBBB'}
`

const HorizontalOnOffToggle = props =>
  <Toggle onClick={props.onClick}>
    {props.isOn ?
      <ToggleIcon size="large" color={props.color} name="toggle on" /> :
      <ToggleIcon size="large" name="toggle off" />
    }
  </Toggle>


HorizontalOnOffToggle.propTypes = {
  onClick: PropTypes.func.isRequired,
  isOn: PropTypes.bool,
  color: PropTypes.string,
}

export default HorizontalOnOffToggle

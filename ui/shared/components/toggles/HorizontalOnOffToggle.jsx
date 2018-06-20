import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { ColoredIcon } from '../StyledComponents'

const Toggle = styled.a.attrs({ role: 'button', tabIndex: '0' })`
  -webkit-user-select: none;
  -moz-user-select: none;
  -khtml-user-select: none;
  -ms-user-select: none;
  cursor: pointer;
  outline: none;
  vertical-align: bottom;
`

const HorizontalOnOffToggle = props =>
  <Toggle onClick={props.onClick}>
    {props.isOn ?
      <ColoredIcon size="large" color={props.color || '#BBBBBB'} name="toggle on" /> :
      <ColoredIcon size="large" color="#BBBBBB" name="toggle off" />
    }
  </Toggle>


HorizontalOnOffToggle.propTypes = {
  onClick: PropTypes.func.isRequired,
  isOn: PropTypes.bool,
  color: PropTypes.string,
}

export default HorizontalOnOffToggle

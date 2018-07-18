import React from 'react'
import styled from 'styled-components'
import { Icon, Label } from 'semantic-ui-react'

export const ColoredIcon = styled(({ color, ...props }) => <Icon {...props} />)`
  color: ${props => props.color} !important;
`

export const ColoredLabel = styled(({ color, ...props }) => <Label {...props} />)`
  background-color: ${props => props.color} !important;
  color: white !important;
`

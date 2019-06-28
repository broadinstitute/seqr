import React from 'react'
import styled from 'styled-components'
import { Button, Header, Icon, Label, Table } from 'semantic-ui-react'

export const ButtonLink = styled(({ color, padding, ...props }) => <Button {...props} />).attrs({ basic: true })`
  &.ui.button.basic {
    white-space: nowrap;
    border: none;
    padding: ${props => props.padding || 0};
    color: ${props => props.color || '#4183C4'} !important;
    text-decoration: none;
    font-weight: ${props => props.fontWeight || 'inherit'};
    box-shadow: none !important;
    user-select: auto;
    
    &:hover, &:focus, &:active {
      color: #1e70bf !important;
      background: transparent !important;
    }
    
    &[class*="right labeled"].icon {
      padding-left: 0 !important;
      padding-right: 2.1em !important;
      
      > .icon {
        background-color: initial;
      }
    }
  }
`

export const ColoredIcon = styled(({ color, ...props }) => <Icon {...props} />)`
  color: ${props => props.color} !important;
`

export const ColoredLabel = styled(({ color, ...props }) => <Label {...props} />)`
  background-color: ${props => props.color} !important;
  color: white !important;
`

export const ColoredOutlineLabel = styled(({ color, ...props }) => <Label {...props} />)`
  color: ${props => props.color} !important;
  border-color: ${props => props.color} !important;
`

export const HelpIcon = styled(Icon).attrs({ name: 'help circle outline', color: 'grey' })`
  cursor: pointer;
  margin-left: 5px !important;
`

export const NoBorderTable = styled(Table)`
  border: none !important;
  
  td {
    border: none !important;
  }
`

export const InlineHeader = styled(({ overrideInline, ...props }) => <Header {...props} />)`
  display: ${props => (props.overrideInline ? 'block' : 'inline-block')};
  margin-right: 1em !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  
  .sub.header {
    display: inline-block !important;
    margin-left: 0.5em !important;
  }
`

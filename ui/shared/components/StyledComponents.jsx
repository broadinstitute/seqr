import React from 'react'
import styled from 'styled-components'
import { Button, Header, Icon, Label, Table } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

const BaseButtonLink = styled(({ color, padding, ...props }) => <Button {...props} />).attrs(
  props => (props.as ? {} : { basic: true }),
)`
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
// This notation required to fix a ref forwarding bug with styled components and seamntic ui: https://github.com/Semantic-Org/Semantic-UI-React/issues/3786#issuecomment-557560471
export const ButtonLink = props => <BaseButtonLink {...props} />

const BaseColoredComponent = styled.div`
  color: ${props => props.color} !important;
`

const ColoredComponent = control => BaseColoredComponent.withComponent(({ color, ...props }) => React.createElement(control, props))

const BaseColoredIcon = ColoredComponent(Icon)
export const ColoredIcon = props => <BaseColoredIcon {...props} />

const BaseColoredLink = ColoredComponent(NavLink)
export const ColoredLink = props => <BaseColoredLink {...props} />


const BaseColoredLabel = styled(({ color, ...props }) => <Label {...props} />)`
  background-color: ${props => props.color} !important;
  color: white !important;
`
export const ColoredLabel = props => <BaseColoredLabel {...props} />

const BaseColoredOutlineLabel = styled(({ color, ...props }) => <Label {...props} />)`
  color: ${props => props.color} !important;
  border-color: ${props => props.color} !important;
`
export const ColoredOutlineLabel = props => <BaseColoredOutlineLabel {...props} />


const BaseHelpIcon = styled(Icon).attrs({ name: 'question circle outline', color: 'grey' })`
  cursor: pointer;
  margin-left: 5px !important;
`
// This notation required to fix a ref forwarding bug with styled components and seamntic ui: https://github.com/Semantic-Org/Semantic-UI-React/issues/3786#issuecomment-557560471
export const HelpIcon = props => <BaseHelpIcon {...props} />

export const NoBorderTable = styled(Table)`
  border: none !important;
  
  td {
    border: none !important;
  }
`

export const InlineHeader = styled(Header)`
  display: inline-block;
  margin-right: 1em !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  
  .sub.header {
    display: inline-block !important;
    margin-left: 0.5em !important;
  }
`

export const SectionHeader = styled.div`
  padding-top: 8px;
  padding-bottom: 6px;
  margin: 8px 0 15px 0;
  border-bottom: 1px solid #EEE;
  font-family: 'Lato';
  font-weight: 300;
  font-size: 18px; 
`

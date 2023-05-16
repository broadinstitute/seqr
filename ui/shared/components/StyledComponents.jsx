import React from 'react'

import styled from 'styled-components'
import { Button, Header, Icon, Label, Table } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

const BaseButtonLink = styled(({ color, padding, ...props }) => <Button {...props} />).attrs(
  props => (props.as ? { className: `ui button basic${props.disabled ? ' disabled' : ''}` } : { basic: true }),
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

export const ColoredDiv = styled.div`
  color: ${props => props.color} !important;
`

const ColoredComponent = control => ColoredDiv.withComponent(
  ({ color, ...props }) => React.createElement(control, props),
)

const BaseColoredIcon = ColoredComponent(Icon)
export const ColoredIcon = props => <BaseColoredIcon {...props} />

const BaseColoredLink = ColoredComponent(NavLink)
export const ColoredLink = props => <BaseColoredLink {...props} />

const BaseColoredLabel = styled(({ color, minWidth, ...props }) => <Label {...props} />)`
  background-color: ${props => props.color} !important;
  min-width:  ${props => props.minWidth || 'auto'} !important;
  color: white !important;
`
export const ColoredLabel = props => <BaseColoredLabel {...props} />

const BaseColoredOutlineLabel = styled(({ color, ...props }) => <Label {...props} />)`
  color: ${props => props.color} !important;
  border-color: ${props => props.color} !important;
`
export const ColoredOutlineLabel = props => <BaseColoredOutlineLabel {...props} />

const BaseHelpIcon = styled(Icon).attrs(({ color }) => ({ name: 'question circle outline', color: color || 'grey' }))`
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

// Map font-awesome icons to semantic-ui icons
export const FontAwesomeIconsContainer = styled.div`
  .fa {
    display: inline-block;
    opacity: 1;
    margin: 0em 0.25rem 0em 0em;
    width: 1.18em;
    height: 1em;
    font-family: 'Icons';
    font-style: normal;
    font-weight: normal;
    text-decoration: inherit;
    text-align: center;
    speak: none;
    font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    -webkit-font-smoothing: antialiased;
    -webkit-backface-visibility: hidden;
    backface-visibility: hidden;
  }
  
  .fa:before {
    background: none !important;
  }
  
  .fa-fw {
    width: 1.2857142857142858em;
    text-align: center;
  }
  
  .fa-lg {
    font-size: 1.33333333em;
    line-height: .75em;
    vertical-align: -15%;
  }
  
  .fa-2x {
    font-size: 2em;
  }
  
  .fa.pull-right {
    margin-left: .3em;
    float: right;
  }
  
  .fa.pull-left {
    margin-right: .3em;
    float: left;
  }
  
  .fa-spin  {
    height: 1em;
    line-height: 1;
    -webkit-animation: icon-loading 2s linear infinite;
    animation: icon-loading 2s linear infinite;
  }
  
  .fa-check:before {
    content: "\\f00c";
  }
  .fa-square:before {
    content: "\\f098";
  } 
  .fa-search:before {
    content: "\\f002";
  }
  .fa-minus-circle:before {
    content: "\\f056";
  } 
  .fa-plus-circle:before  {
    content: "\\f055";
  }
  .fa-times:before  {
    content: "\\f00d";
  }  
  .fa-times-circle:before  {
    content: "\\f057";
  } 
  .fa-gear:before  {
    content: "\\f013";
  }
  .fa-exclamation-triangle:before  {
    content: "\\f071";
  }  
  .fa-spinner:before  {
    content: "\\f110";
  }
  .fa-undo:before  {
    content: "\\f0e2";
  }  
  .fa-repeat:before  {
    content: "\\f01e";
  } 
  .fa-refresh:before  {
    content: "\\f021";
  } 
  .fa-arrows-alt:before  {
    content: "\\f31e";
  }  
  .fa-crosshairs:before  {
    content: "\\f05b";
  } 
`

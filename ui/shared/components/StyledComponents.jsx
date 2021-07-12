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


// Map font-awesome icons to semantic-ui icons
export const FontAwesomeIconsContainer = styled.div`
  i.fa {
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
  
  i.fa:before {
    background: none !important;
  }
  
  i.fa-fw {
    width: 1.2857142857142858em;
    text-align: center;
  }
  
  i.fa-lg {
    line-height: 1;
    vertical-align: middle;
    font-size: 1.5em;
  }
  
  i.fa-2x {
    font-size: 2em;
  }
  
  i.fa-spin  {
    height: 1em;
    line-height: 1;
    -webkit-animation: icon-loading 2s linear infinite;
    animation: icon-loading 2s linear infinite;
  }
  
  i.fa-check:before {
    content: "\\f00c";
  }
  i.fa-square:before {
    content: "\\f098";
  } 
  i.fa-search:before {
    content: "\\f002";
  }
  i.fa-minus-circle:before {
    content: "\\f056";
  } 
  i.fa-plus-circle:before  {
    content: "\\f055";
  }
  i.fa-times:before  {
    content: "\\f00d";
  }  
  i.fa-times-circle:before  {
    content: "\\f057";
  } 
  i.fa-gear:before  {
    content: "\\f013";
  }
  i.fa-exclamation-triangle:before  {
    content: "\\f071";
  }  
  i.fa-spinner:before  {
    content: "\\f110";
  }
  i.fa-undo:before  {
    content: "TODO";
  }  
  i.fa-repeat:before  {
    content: "TODO";
  } 
  i.fa-refresh:before  {
    content: "TODO";
  } 
  i.fa-arrows-alt:before  {
    content: "TODO";
  } 
  i.fa-circle:before  {
    content: "TODO";
  } 
  i.fa-crosshairs:before  {
    content: "TODO";
  } 
  i.fa-unspecified:before  {
    content: "TODO";
  } 
  i.fa-angle-up:before  {
    content: "TODO";
  }  
  i.fa-caret-up:before  {
    content: "TODO";
  }

  .igv-zoom-widget i {
    line-height: 24px;
  }
  
`

import React from 'react'
//import { Grid } from 'semantic-ui-react'
//import { connect } from 'react-redux'
//import { bindActionCreators } from 'redux'


const ExportTableLink = props =>
  <a href={props.url}>{props.children}</a>

ExportTableLink.propTypes = {
  children: React.PropTypes.node.isRequired,
  url: React.PropTypes.string.isRequired,
  //onClick: React.PropTypes.func.isRequired,
}

export default ExportTableLink

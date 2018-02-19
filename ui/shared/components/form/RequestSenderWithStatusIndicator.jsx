/**
 React component
 */


import React from 'react'
import PropTypes from 'prop-types'
//import { Grid } from 'semantic-ui-react'
//import { connect } from 'react-redux'

class RequestSenderWithStatusIndicator extends React.Component
{
  static propTypes = {
    loadingIndicator: PropTypes.node,
    errorIndicator: PropTypes.node,
    successIndicator: PropTypes.node,
  }

  constructor(props) {
    super(props)

    this.state = {
      //showModal: false,
    }
  }

  render() {
    return null
  }
}

export default NewComponent
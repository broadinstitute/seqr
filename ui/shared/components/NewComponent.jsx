/** This is an example Component skeleton */

import React from 'react'
//import PropTypes from 'prop-types'
//import { Grid } from 'semantic-ui-react'
//import { connect } from 'react-redux'

class NewComponent extends React.Component
{
  static propTypes = {
    //project: PropTypes.object.isRequired,
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

/*
const mapStateToProps = state => ({ showCategories: state.projectsTableState.showCategories })
const mapDispatchToProps = { onChange: null }
export default connect(mapStateToProps, mapDispatchToProps)(NewComponent)
*/

import React from 'react'
import PropTypes from 'prop-types'

class CollapsableLayout extends React.PureComponent {

  static propTypes = {
    children: PropTypes.node,
  }

  state = { showDetails: false }

  toggle = () => {
    this.setState(prevState => ({ showDetails: !prevState.showDetails }))
  }

  render() {
    const { children } = this.props
    const { showDetails } = this.state
    return React.cloneElement(children, { showDetails, toggleDetails: this.toggle })
  }

}

export default CollapsableLayout

import React from 'react'
import PropTypes from 'prop-types'

class CollapsableLayout extends React.PureComponent {

  static propTypes = {
    layoutComponent: PropTypes.elementType.isRequired,
    detailFields: PropTypes.arrayOf(PropTypes.object).isRequired,
    noDetailFields: PropTypes.arrayOf(PropTypes.object),
  }

  state = { showDetails: false }

  toggle = () => {
    this.setState(prevState => ({ showDetails: !prevState.showDetails }))
  }

  render() {
    const { layoutComponent, detailFields, noDetailFields, ...props } = this.props
    const { showDetails } = this.state
    const allowToggle = !!noDetailFields
    const compact = allowToggle && !showDetails

    return React.createElement(layoutComponent, {
      fields: compact ? noDetailFields : detailFields,
      compact,
      disableEdit: compact,
      toggleDetails: allowToggle ? this.toggle : null,
      ...props,
    })
  }

}

export default CollapsableLayout

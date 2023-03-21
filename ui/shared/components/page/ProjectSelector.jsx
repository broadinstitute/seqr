import React from 'react'
import PropTypes from 'prop-types'

import AwesomeBar from './AwesomeBar'
import { InlineHeader } from '../StyledComponents'

const SEARCH_CATEGORIES = ['projects']

class ProjectSelector extends React.PureComponent {

  static propTypes = {
    layout: PropTypes.elementType,
  }

  state = {}

  onResultSelect = ({ title, key }) => {
    this.setState({ project: { title, guid: key } })
  }

  render() {
    const { layout } = this.props
    const { project } = this.state
    return (
      <div>
        <InlineHeader size="medium" content="Project:" />
        <AwesomeBar
          categories={SEARCH_CATEGORIES}
          placeholder="Enter project name"
          inputwidth="350px"
          onResultSelect={this.onResultSelect}
        />
        {React.createElement(layout, { project })}
      </div>
    )
  }

}

export default ProjectSelector

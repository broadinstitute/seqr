import React from 'react'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'

const SEARCH_CATEGORIES = ['projects']

class Anvil extends React.PureComponent {
  constructor(props) {
    super(props)
    this.state = {}
  }

  onResultSelect = ({ title, key }) => {
    this.setState({ project: { title, guid: key } })
  }

  render() {
    return (
      <div>
        <InlineHeader size="medium" content="Project:" />
        <AwesomeBar
          categories={SEARCH_CATEGORIES}
          placeholder="Enter project name"
          inputwidth="350px"
          onResultSelect={this.onResultSelect}
        />
        <HorizontalSpacer width={20} />
        {this.state.project &&
          <a href={`/api/staff/anvil/${this.state.project.guid}`}>
            Download AnVIL metadata for {this.state.project.title}
          </a>
        }
      </div>
    )
  }
}

export default Anvil

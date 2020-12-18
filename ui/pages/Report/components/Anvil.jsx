import React from 'react'
import { Input } from 'semantic-ui-react'

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

  onDataChange = (e, { value }) => {
    this.setState({ loadedBefore: value })
  }

  render() {
    const { project, loadedBefore } = this.state
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
        <InlineHeader size="medium" content="Loaded Before:" />
        <Input type="date" onChange={this.onDataChange} />
        {project &&
          <div>
            <a href={`/api/report/anvil/${project.guid}?loadedBefore=${loadedBefore || ''}`}>
              Download AnVIL metadata for {project.title}
            </a>
          </div>
        }
      </div>
    )
  }
}

export default Anvil

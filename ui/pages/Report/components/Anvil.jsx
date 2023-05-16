import React from 'react'
import PropTypes from 'prop-types'
import { Input } from 'semantic-ui-react'

import ProjectSelector from 'shared/components/page/ProjectSelector'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'

class AnvilDownload extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object,
  }

  state = {}

  onDataChange = (e, { value }) => {
    this.setState({ loadedBefore: value })
  }

  render() {
    const { project } = this.props
    const { loadedBefore } = this.state
    return (
      <span>
        <HorizontalSpacer width={20} />
        <InlineHeader size="medium" content="Loaded Before:" />
        <Input type="date" onChange={this.onDataChange} />
        {project && (
          <div>
            <a href={`/api/report/anvil/${project.guid}?loadedBefore=${loadedBefore || ''}`}>
              {`Download AnVIL metadata for ${project.title}`}
            </a>
          </div>
        )}
      </span>
    )
  }

}

export default () => <ProjectSelector layout={AnvilDownload} />

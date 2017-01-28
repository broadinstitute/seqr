import React from 'react'
import { Table } from 'semantic-ui-react'

import ProjectPageLink from './ProjectPageLink'
import EllipsisMenu from './ProjectEllipsisMenu'
import { formatDate } from '../../../shared/utils/dateUtils'

class ProjectsTableRow extends React.PureComponent {

  static propTypes = {
    //user: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
  }

  shouldComponentUpdate(nextProps) {
    return this.props.project !== nextProps.project
  }

  render() {
    const project = this.props.project
    return <Table.Row style={{ padding: '5px 0px 15px 15px' }}>
      <Table.Cell>
        <div style={{ color: '#555555' }}>
          <div className="text-column-value">
            <ProjectPageLink project={project} />
            { project.description && (<span style={{ marginLeft: '10px' }}>{project.description}</span>)}
          </div>
        </div>
      </Table.Cell>
      <Table.Cell>
        <div className="numeric-column-value">{project.numFamilies}</div>
      </Table.Cell>
      <Table.Cell>
        <div className="numeric-column-value">{project.numIndividuals}</div>
      </Table.Cell>
      <Table.Cell>
        <div className="numeric-column-value">
          <div style={{ minWidth: '70px' }}>
            {project.datasets && project.datasets.map((d, i) => {
              const color = (d.sequencingType === 'WES' && '#73AB3D') || (d.sequencingType === 'WGS' && '#4682b4') || 'black'
              return <span key={i} style={{ color }}>
                {`${d.isLoaded ? d.numSamples : d.numSamples} `}
                <b>{`${d.sequencingType}`}</b>
              </span>
            })}
          </div>
        </div>
      </Table.Cell>
      <Table.Cell>
        <div className="text-column-value" style={{ minWidth: '150px' }}>
          {formatDate('', project.createdDate, false)}
          <span style={{ float: 'right' }}><EllipsisMenu projectGuid={project.projectGuid} /></span>
        </div>
      </Table.Cell>
    </Table.Row>
  }
}

export default ProjectsTableRow

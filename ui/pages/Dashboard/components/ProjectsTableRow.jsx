import React from 'react'
import { Table } from 'semantic-ui-react'

import ProjectPageLink from './ProjectPageLink'
import EllipsisMenu from './ProjectEllipsisMenu'
import { formatDate } from '../../../shared/utils/dateUtils'

class ProjectsTableRow extends React.PureComponent {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
  }

  shouldComponentUpdate(nextProps) {
    return this.props.project !== nextProps.project
  }

  render() {
    const project = this.props.project
    return <Table.Row style={{ padding: '5px 0px 15px 15px' }}>
      <Table.Cell />
      <Table.Cell>
        <div className="text-column-value">
          <ProjectPageLink project={project} />
          { project.description && (<span style={{ marginLeft: '10px' }}>{project.description}</span>)}
        </div>
      </Table.Cell>
      <Table.Cell>
        <div className="numeric-column-value">
          {formatDate('', project.createdDate, false)}
        </div>
      </Table.Cell>
      {
        this.props.user.is_staff &&
        <Table.Cell collapsing>
          <div className="numeric-column-value">
            {formatDate('', project.lastAccessedDate, false)}
          </div>
        </Table.Cell>
      }
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
        <div style={{ color: 'gray', whiteSpace: 'nowrap', width: '135px', marginRight: '0px' }}>
          <div style={{ display: 'inline-block', width: '67px', textAlign: 'left' }}>{project.numFamilies ? parseInt((100.0 * project.numFamiliesSolved) / project.numFamilies, 10) : 0}% solved,</div>
          <div style={{ display: 'inline-block', width: '67px', textAlign: 'right' }}>{project.numVariantTags} tags</div>
          {/* this.props.user.is_staff && formatDate('', project.lastAccessedDate, false) */}
        </div>
      </Table.Cell>
      <Table.Cell>
        <span style={{ float: 'right' }}>
          <EllipsisMenu projectGuid={project.projectGuid} />
        </span>
      </Table.Cell>
    </Table.Row>
  }
}

export default ProjectsTableRow

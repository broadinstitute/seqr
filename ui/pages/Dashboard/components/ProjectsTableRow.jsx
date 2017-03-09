/* eslint-disable no-unused-expressions */
import React from 'react'
import { Table } from 'semantic-ui-react'

import CategoryIndicator from './CategoryIndicator'
import ProjectPageLink from './ProjectPageLink'
import EllipsisMenu from './ProjectEllipsisMenu'
import { FAMILY_ANALYSIS_STATUS_OPTIONS } from '../constants'

import HorizontalStackedBar from '../../../shared/components/HorizontalStackedBar'

import { formatDate } from '../../../shared/utils/dateUtils'

class ProjectsTableRow extends React.PureComponent {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
    sampleBatchesByGuid: React.PropTypes.object.isRequired,
  }

  shouldComponentUpdate(nextProps) {
    return this.props.project !== nextProps.project
  }

  render() {
    const project = this.props.project
    const analysisStatusCounts = project.analysisStatusCounts && FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
      (acc, d) => (
        project.analysisStatusCounts[d.key] ?
          [...acc, { ...d, count: project.analysisStatusCounts[d.key] }] :
          acc
      ), [])

    return <Table.Row style={{ padding: '5px 0px 15px 15px' }}>
      <Table.Cell><CategoryIndicator project={project} /></Table.Cell>
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
            {formatDate('', project.deprecatedLastAccessedDate, false)}
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
            {project.sampleBatchGuids && project.sampleBatchGuids.map((sampleBatchGuid, i) => {
              const d = this.props.sampleBatchesByGuid[sampleBatchGuid]
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
        <div className="numeric-column-value">{project.numVariantTags}</div>
      </Table.Cell>
      <Table.Cell>
        <div style={{ color: 'gray', whiteSpace: 'nowrap', marginRight: '0px' }}>
          <div style={{ display: 'inline-block', width: '67px', textAlign: 'left' }}>
            {analysisStatusCounts && <HorizontalStackedBar
              title="Family Analysis Status"
              data={analysisStatusCounts}
              width={67}
              height={10}
            />}
          </div>
          {/* this.props.user.is_staff && formatDate('', project.deprecatedLastAccessedDate, false) */}
        </div>
      </Table.Cell>
      <Table.Cell>
        <span style={{ float: 'right' }}>
          <EllipsisMenu project={project} />
        </span>
      </Table.Cell>
    </Table.Row>
  }
}

export default ProjectsTableRow

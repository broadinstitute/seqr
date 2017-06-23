import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'
import orderBy from 'lodash/orderBy'
import Timeago from 'timeago.js'

import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/constants/familyAndIndividualConstants'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { computeProjectUrl } from 'shared/utils/urlUtils'

import CategoryIndicator from './CategoryIndicator'
import ProjectEllipsisMenu from './ProjectEllipsisMenu'
import { getUser, getSampleBatchesByGuid } from '../../reducers/rootReducer'

const numericColumnValue = {
  color: 'gray',
  marginRight: '23px',
  textAlign: 'right',
  verticalAlign: 'top',
  whiteSpace: 'nowrap',
}

const textColumnValue = {
  color: 'gray',
  verticalAlign: 'top',
}


class ProjectTableRow extends React.PureComponent {

  static propTypes = {
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    sampleBatchesByGuid: PropTypes.object.isRequired,
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

    return <Table.Row style={{ padding: '5px 0px 15px 15px', verticalAlign: 'top' }}>
      <Table.Cell collapsing>
        <CategoryIndicator project={project} />
      </Table.Cell>
      <Table.Cell>
        <div style={textColumnValue}>
          <a href={computeProjectUrl(this.props.project.projectGuid)}>{this.props.project.name}</a>
          { project.description && (<span style={{ marginLeft: '10px' }}>{project.description}</span>)}
        </div>
      </Table.Cell>
      <Table.Cell collapsing>
        <div style={numericColumnValue}>
          {new Timeago().format(project.createdDate)}
        </div>
      </Table.Cell>
      {
        this.props.user.is_staff &&
        <Table.Cell collapsing>
          <div style={numericColumnValue}>
            {new Timeago().format(project.deprecatedLastAccessedDate)}
          </div>
        </Table.Cell>
      }
      <Table.Cell collapsing>
        <div style={numericColumnValue}>{project.numFamilies}</div>
      </Table.Cell>
      <Table.Cell collapsing>
        <div style={numericColumnValue}>{project.numIndividuals}</div>
      </Table.Cell>
      <Table.Cell collapsing>
        <div style={numericColumnValue}>
          <div style={{ minWidth: '70px' }}>
            {
              project.sampleBatchGuids &&
              orderBy(
                project.sampleBatchGuids, [guid => this.props.sampleBatchesByGuid[guid].sampleType], ['asc'],
              ).map((sampleBatchGuid, i) => {
                const sb = this.props.sampleBatchesByGuid[sampleBatchGuid]
                const color = (sb.sampleType === 'WES' && '#73AB3D') || (sb.sampleType === 'WGS' && '#4682b4') || 'black'
                return <span key={sampleBatchGuid}><span style={{ color }}>{sb.numSamples} <b>{sb.sampleType}</b></span>
                  {(i < project.sampleBatchGuids.length - 1) ? ', ' : null}</span>
              })
            }
          </div>
        </div>
      </Table.Cell>
      <Table.Cell collapsing>
        <div style={numericColumnValue}>{project.numVariantTags}</div>
      </Table.Cell>
      <Table.Cell collapsing>
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
      <Table.Cell collapsing>
        <span style={{ float: 'right' }}>
          {(this.props.user.is_staff || this.props.project.canEdit) && <ProjectEllipsisMenu project={project} />}
        </span>
      </Table.Cell>
    </Table.Row>
  }
}

export { ProjectTableRow as ProjectTableRowComponent }

const mapStateToProps = state => ({
  user: getUser(state),
  sampleBatchesByGuid: getSampleBatchesByGuid(state),
})

export default connect(mapStateToProps)(ProjectTableRow)

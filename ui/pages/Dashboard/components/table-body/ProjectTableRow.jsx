import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'
import Timeago from 'timeago.js'
import { Link } from 'react-router-dom'


import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/constants/familyAndIndividualConstants'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { computeProjectUrl } from 'shared/utils/urlUtils'
import { getUser } from 'redux/rootReducer'

import CategoryIndicator from './CategoryIndicator'
import ProjectEllipsisMenu from './ProjectEllipsisMenu'

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


class ProjectTableRow extends React.Component {

  static propTypes = {
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
  }

  render() {
    const { project } = this.props
    const analysisStatusDataWithCountKey = project.analysisStatusCounts && FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
      (acc, d) => (
        project.analysisStatusCounts[d.key] ?
          [...acc, { ...d, count: project.analysisStatusCounts[d.key] }] :
          acc
      ), [])

    return (
      <Table.Row style={{ padding: '5px 0px 15px 15px', verticalAlign: 'top' }}>
        <Table.Cell collapsing>
          <CategoryIndicator project={project} />
        </Table.Cell>
        <Table.Cell>
          <div style={textColumnValue}>
            <Link to={`/project/${this.props.project.projectGuid}/project_page`}>{this.props.project.name}</Link>
            { project.description && (<span style={{ marginLeft: '10px' }} />)}
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
                project.sampleTypeCounts &&
                Object.entries(project.sampleTypeCounts).map(([sampleType, numSamples], i) => {
                  const color = (sampleType === 'WES' && '#73AB3D') || (sampleType === 'WGS' && '#4682b4') || 'black'
                  return (
                    <span key={sampleType}>
                      <span style={{ color }}>{numSamples} <b>{sampleType}</b></span>
                      {(i < project.sampleTypeCounts.length - 1) ? ', ' : null}
                    </span>)
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
              {analysisStatusDataWithCountKey && <HorizontalStackedBar
                title="Family Analysis Status"
                data={analysisStatusDataWithCountKey}
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
      </Table.Row>)
  }
}

export { ProjectTableRow as ProjectTableRowComponent }

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(ProjectTableRow)

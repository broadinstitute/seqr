import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'
import Timeago from 'timeago.js'
import { Link } from 'react-router-dom'


import { FAMILY_ANALYSIS_STATUS_OPTIONS } from 'shared/utils/constants'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { getUser } from 'redux/selectors'
import { HorizontalSpacer } from 'shared/components/Spacers'

import CategoryIndicator from './CategoryIndicator'
import ProjectEllipsisMenu from './ProjectEllipsisMenu'

const GrayRow = styled(Table.Row)`
  color: gray;
`


class ProjectTableRow extends React.Component {

  static propTypes = {
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
  }

  render() {
    const { project } = this.props
    const analysisStatusDataWithCountKey = project.analysisStatusCounts && FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
      (acc, d) => (
        project.analysisStatusCounts[d.value] ?
          [...acc, { ...d, count: project.analysisStatusCounts[d.value] }] :
          acc
      ), [])

    return (
      <GrayRow verticalAlign="top">
        <Table.Cell collapsing>
          <CategoryIndicator project={project} />
        </Table.Cell>
        <Table.Cell>
          <Link to={`/project/${this.props.project.projectGuid}/project_page`}>{this.props.project.name}</Link>
          <HorizontalSpacer width={10} />
          { project.description }
        </Table.Cell>
        <Table.Cell collapsing textAlign="right">
          {new Timeago().format(project.createdDate)}
        </Table.Cell>
        {
          this.props.user.is_staff &&
          <Table.Cell collapsing textAlign="right">
            {new Timeago().format(project.deprecatedLastAccessedDate)}
          </Table.Cell>
        }
        <Table.Cell collapsing textAlign="right">
          {project.numFamilies}
        </Table.Cell>
        <Table.Cell collapsing textAlign="right">
          {project.numIndividuals}
        </Table.Cell>
        <Table.Cell collapsing textAlign="right">
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
        </Table.Cell>
        <Table.Cell collapsing textAlign="right">
          {project.numVariantTags}
        </Table.Cell>
        <Table.Cell collapsing>
          {analysisStatusDataWithCountKey && <HorizontalStackedBar
            title="Family Analysis Status"
            data={analysisStatusDataWithCountKey}
            width={67}
            height={12}
          />}
          {/* this.props.user.is_staff && formatDate('', project.deprecatedLastAccessedDate, false) */}
        </Table.Cell>
        <Table.Cell collapsing textAlign="right">
          {(this.props.user.is_staff || this.props.project.canEdit) && <ProjectEllipsisMenu project={project} />}
        </Table.Cell>
      </GrayRow>)
  }
}

export { ProjectTableRow as ProjectTableRowComponent }

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(ProjectTableRow)

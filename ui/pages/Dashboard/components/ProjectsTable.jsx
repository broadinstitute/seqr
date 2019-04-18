import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import Timeago from 'timeago.js'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getProjectsIsLoading, getUser } from 'redux/selectors'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import SortableTable from 'shared/components/table/SortableTable'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'
import { FAMILY_ANALYSIS_STATUS_OPTIONS, SAMPLE_TYPE_EXOME, SAMPLE_TYPE_GENOME } from 'shared/utils/constants'

import CreateProjectButton from './CreateProjectButton'
import FilterSelector from './FilterSelector'
import CategoryIndicator from './CategoryIndicator'
import ProjectEllipsisMenu from './ProjectEllipsisMenu'
import { getVisibleProjects } from '../utils/visibleProjectsSelector'


const RightAligned = styled.span`
  float: right;
`

const ProjectTableContainer = styled.div`
  th {
    padding: 12px 10px 12px 3px !important; 
    font-weight: 500 !important;
  }
  
  tr {
    color: gray;
    
    td {
      overflow: visible !important;
    }
  }
  
  tfoot th {
    padding-right: 45px !important;
    font-weight: 300 !important;
    border-top: none !important;
  }
`

const PROJECT_EXPORT_URLS = [{ name: 'Projects', url: '/api/dashboard/export_projects_table' }]

const COLUMNS = [
  {
    name: 'projectCategoryGuids',
    width: 1,
    format: project => <CategoryIndicator project={project} />,
  },
  {
    name: 'name',
    width: 5,
    content: 'Name',
    format: project => (
      <div>
        <Link to={`/project/${project.projectGuid}/project_page`}>{project.name}</Link>
        <HorizontalSpacer width={10} />
        { project.description }
      </div>
    ),
  },
  {
    name: 'createdDate',
    width: 2,
    content: 'Created',
    textAlign: 'right',
    format: project => new Timeago().format(project.createdDate),
  },
  {
    name: 'numFamilies',
    width: 1,
    content: 'Fam.',
    textAlign: 'right',
  },
  {
    name: 'numIndividuals',
    width: 1,
    content: 'Indiv.',
    textAlign: 'right',
  },
  {
    name: 'sampleTypeCounts',
    width: 1,
    content: 'Samples',
    textAlign: 'right',
    format: project => project.sampleTypeCounts && Object.entries(project.sampleTypeCounts).map(
      ([sampleType, numSamples], i) => {
        const color = (sampleType === SAMPLE_TYPE_EXOME && '#73AB3D') || (sampleType === SAMPLE_TYPE_GENOME && '#4682b4') || 'black'
        return (
          <div key={sampleType}>
            <span style={{ color }}>{numSamples} <b>{sampleType}</b></span>
            {(i < project.sampleTypeCounts.length - 1) ? ', ' : null}
          </div>)
      }),
  },
  {
    name: 'numVariantTags',
    width: 1,
    content: 'Tags',
    textAlign: 'right',
  },
  {
    name: 'analysisStatusCounts',
    width: 1,
    content: 'Analysis',
    textAlign: 'right',
    format: project => project.analysisStatusCounts && (
      <HorizontalStackedBar
        title="Family Analysis Status"
        data={FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
          (acc, d) => (
            project.analysisStatusCounts[d.value] ?
              [...acc, { ...d, count: project.analysisStatusCounts[d.value] }] :
              acc
          ), [])}
        height={12}
      />
    ),
  },
  {
    name: 'edit',
    width: 1,
    textAlign: 'right',
    format: project => project.canEdit && <ProjectEllipsisMenu project={project} />,
  },
]

const STAFF_COLUMNS = [...COLUMNS]
STAFF_COLUMNS.splice(3, 0, {
  name: 'lastAccessedDate',
  width: 2,
  content: 'Last Accessed',
  textAlign: 'right',
  format: project => (project.lastAccessedDate ? new Timeago().format(project.lastAccessedDate) : ''),
})

const ProjectsTable = ({ visibleProjects, loading, user }) =>
  <ProjectTableContainer>
    <VerticalSpacer height={10} />
    <HorizontalSpacer width={10} />
    <InlineHeader size="medium" content="Projects:" />
    <FilterSelector />
    <RightAligned>
      <ExportTableButton downloads={PROJECT_EXPORT_URLS} />
      <HorizontalSpacer width={45} />
    </RightAligned>
    <VerticalSpacer height={10} />
    <SortableTable
      striped
      stackable
      fixed
      idField="projectGuid"
      defaultSortColumn="name"
      emptyContent="0 projects found"
      loading={loading}
      data={visibleProjects}
      columns={user.isStaff ? STAFF_COLUMNS : COLUMNS}
      footer={user.isStaff ? <CreateProjectButton /> : null}
    />
  </ProjectTableContainer>

ProjectsTable.propTypes = {
  visibleProjects: PropTypes.array.isRequired,
  loading: PropTypes.bool.isRequired,
  user: PropTypes.object,
}

export { ProjectsTable as ProjectsTableComponent }

const mapStateToProps = state => ({
  visibleProjects: getVisibleProjects(state),
  loading: getProjectsIsLoading(state),
  user: getUser(state),
})

export default connect(mapStateToProps)(ProjectsTable)

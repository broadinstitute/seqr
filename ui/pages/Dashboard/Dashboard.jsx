import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import Timeago from 'timeago.js'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Popup, Icon } from 'semantic-ui-react'

import { fetchProjects } from 'redux/rootReducer'
import { getProjectsIsLoading, getUser, getOauthLoginEnabled } from 'redux/selectors'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import DataTable from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { InlineHeader, ColoredDiv } from 'shared/components/StyledComponents'
import { ALL_FAMILY_ANALYSIS_STATUS_OPTIONS, SAMPLE_TYPE_EXOME, SAMPLE_TYPE_GENOME } from 'shared/utils/constants'

import CreateProjectButton from './components/CreateProjectButton'
import FilterSelector from './components/FilterSelector'
import CategoryIndicator from './components/CategoryIndicator'
import ProjectEllipsisMenu from './components/ProjectEllipsisMenu'
import { getVisibleProjects } from './selectors'

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

const COLUMNS = [
  {
    name: 'projectCategories',
    width: 1,
    format: project => <CategoryIndicator project={project} />,
    downloadColumn: 'Categories',
    noFormatExport: true,
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
    noFormatExport: true,
  },
  {
    name: 'anvil',
    width: 1,
    content: 'AnVIL',
    format: (project, isExport) => {
      if (!project.workspaceName) {
        return null
      }
      const workspace = `${project.workspaceNamespace}/${project.workspaceName}`
      return (
        isExport ? workspace :
        <Popup content={`AnVIL workspace: ${workspace}`} position="top center" trigger={<Icon name="fire" />} />
      )
    },
  },
  {
    name: 'createdDate',
    width: 2,
    content: 'Created',
    textAlign: 'right',
    format: project => new Timeago().format(project.createdDate),
    noFormatExport: true,
  },
  {
    name: 'numFamilies',
    width: 1,
    content: 'Fam.',
    downloadColumn: 'Families',
    textAlign: 'right',
  },
  {
    name: 'numIndividuals',
    width: 1,
    content: 'Indiv.',
    downloadColumn: 'Individuals',
    textAlign: 'right',
  },
  {
    name: 'sampleTypeCounts',
    width: 1,
    content: 'Samples',
    textAlign: 'right',
    format: (project, isExport) => {
      if (!project.sampleTypeCounts) {
        return null
      }
      if (isExport) {
        return Object.entries(project.sampleTypeCounts).map(
          ([sampleType, numSamples]) => `${sampleType}: ${numSamples}`,
        ).join(', ')
      }
      return Object.entries(project.sampleTypeCounts).map(
        ([sampleType, numSamples], i) => {
          const color = (sampleType === SAMPLE_TYPE_EXOME && '#73AB3D') || (sampleType === SAMPLE_TYPE_GENOME && '#4682b4') || 'black'
          return (
            <div key={sampleType}>
              <ColoredDiv color={color}>
                {numSamples}
                &nbsp;
                <b>{sampleType}</b>
              </ColoredDiv>
              {(i < project.sampleTypeCounts.length - 1) ? ', ' : null}
            </div>
          )
        },
      )
    },
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
    downloadColumn: 'Analysis Status',
    textAlign: 'right',
    format: (project, isExport) => {
      if (!project.analysisStatusCounts) {
        return null
      }
      const statusData = ALL_FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
        (acc, d) => (
          project.analysisStatusCounts[d.value] ?
            [...acc, { ...d, count: project.analysisStatusCounts[d.value] }] :
            acc
        ), [],
      )
      if (isExport) {
        return statusData.map(({ name, count }) => `${name}: ${count}`).join(', ')
      }
      return <HorizontalStackedBar title="Family Analysis Status" data={statusData} height={12} />
    },
  },
  {
    name: 'canEdit',
    width: 1,
    textAlign: 'right',
    format: project => <ProjectEllipsisMenu project={project} />,
    downloadColumn: 'Can Edit',
    noFormatExport: true,
  },
]

const SUPERUSER_COLUMNS = [...COLUMNS]
SUPERUSER_COLUMNS.splice(3, 0, {
  name: 'lastAccessedDate',
  width: 2,
  content: 'Last Accessed',
  textAlign: 'right',
  format: project => (project.lastAccessedDate ? new Timeago().format(project.lastAccessedDate) : ''),
  noFormatExport: true,
})

const COLUMNS_NO_ANVIL = [...COLUMNS]
COLUMNS_NO_ANVIL.splice(2, 1)

const SUPERUSER_COLUMNS_NO_ANVIL = [...SUPERUSER_COLUMNS]
SUPERUSER_COLUMNS_NO_ANVIL.splice(2, 1)

const getColumns = (oauthLoginEnabled, isAnvil, isSuperuser) => {
  if (oauthLoginEnabled && isAnvil) {
    return isSuperuser ? SUPERUSER_COLUMNS : COLUMNS
  }
  return isSuperuser ? SUPERUSER_COLUMNS_NO_ANVIL : COLUMNS_NO_ANVIL
}

const ProjectsTable = React.memo(({ visibleProjects, loading, load, user, oauthLoginEnabled }) => (
  <DataLoader content load={load} loading={false}>
    <ProjectTableContainer>
      <VerticalSpacer height={10} />
      <HorizontalSpacer width={10} />
      <InlineHeader size="medium" content="Projects:" />
      <FilterSelector />
      <VerticalSpacer height={10} />
      <DataTable
        striped
        stackable
        fixed
        idField="projectGuid"
        defaultSortColumn="name"
        emptyContent="0 projects found"
        loading={loading}
        data={visibleProjects}
        columns={getColumns(oauthLoginEnabled, user.isAnvil, user.isSuperuser)}
        footer={user.isPm ? <CreateProjectButton /> : null}
        downloadTableType="Projects"
        downloadFileName="projects"
      />
    </ProjectTableContainer>
  </DataLoader>
))

ProjectsTable.propTypes = {
  visibleProjects: PropTypes.arrayOf(PropTypes.object).isRequired,
  loading: PropTypes.bool.isRequired,
  user: PropTypes.object,
  load: PropTypes.func,
  oauthLoginEnabled: PropTypes.bool,
}

export { ProjectsTable as ProjectsTableComponent }

const mapStateToProps = state => ({
  visibleProjects: getVisibleProjects(state),
  loading: getProjectsIsLoading(state),
  user: getUser(state),
  oauthLoginEnabled: getOauthLoginEnabled(state),
})

const mapDispatchToProps = {
  load: fetchProjects,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectsTable)

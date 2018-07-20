import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Loader } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

import SectionHeader from 'shared/components/SectionHeader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import VariantTagTypeBar from 'shared/components/graph/VariantTagTypeBar'
import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_DETAIL_FIELDS,
} from 'shared/utils/constants'
import {
  getProject,
  getProjectDetailsIsLoading,
  getAnalysisStatusCounts,
  getFamiliesExportConfig,
  getIndividualsExportConfig,
} from '../selectors'
import ProjectOverview from './ProjectOverview'
import ProjectCollaborators from './ProjectCollaborators'
import GeneLists from './GeneLists'
import FamilyTable from './FamilyTable/FamilyTable'
import VariantTags from './VariantTags'


/**
Add charts:
- variant tags - how many families have particular tags
- analysis status
 Phenotypes:
   Cardio - 32 individuals
   Eye - 10 individuals
   Ear - 5 individuals
   Neuro - 10 individuals
   Other - 5 individuals

 Data:
    Exome - HaplotypeCaller variant calls (32 samples), read viz (10 samples)
    Whole Genome - HaplotypeCaller variant calls (32 samples), Manta SV calls (10 samples), read data (5 samples)
    RNA - HaplotypeCaller variant calls (32 samples)

Phenotypes:
- how many families have phenotype terms in each category

What's new:
 - variant tags

*/

const ProjectSectionComponent = ({ loading, label, children, editPath, linkPath, linkText, project }) => {
  return ([
    <SectionHeader key="header">{label}</SectionHeader>,
    <div key="content">
      {loading ? <Loader key="content" inline active /> : children}
    </div>,
    editPath && project.canEdit ? (
      <a key="edit" href={`/project/${project.deprecatedProjectId}/${editPath}`}>
        <VerticalSpacer height={15} />
        {`Edit ${label}`}
      </a>
    ) : null,
    linkText ? (
      <div key="link">
        <VerticalSpacer height={15} />
        <HorizontalSpacer width={35} />
        <Link to={`/project/${project.projectGuid}/${linkPath}`}>{linkText}</Link>
      </div>
    ) : null,
  ])
}

const mapSectionStateToProps = state => ({
  project: getProject(state),
  loading: getProjectDetailsIsLoading(state),
})

const ProjectSection = connect(mapSectionStateToProps)(ProjectSectionComponent)

const NO_DETAIL_FIELDS = [
  { id: FAMILY_FIELD_ANALYSIS_STATUS },
  { id: FAMILY_FIELD_ANALYSED_BY, colWidth: 2 },
  { id: FAMILY_FIELD_FIRST_SAMPLE },
  { id: FAMILY_FIELD_DESCRIPTION, colWidth: 6 },
]

const ProjectPageUI = (props) => {
  const headerStatus = { title: 'Analysis Statuses', data: props.analysisStatusCounts }
  const exportUrls = [
    { name: 'Families', data: props.familyExportConfig },
    { name: 'Individuals', data: props.individualsExportConfig },
  ]

  return (
    <Grid stackable>
      <Grid.Row>
        <Grid.Column width={12}>
          <ProjectSection label="Overview">
            <ProjectOverview />
          </ProjectSection>
          <ProjectSection label="Variant Tags" linkPath="saved_variants" linkText="View All">
            <VariantTagTypeBar project={props.project} height={30} showAllPopupCategories />
            <VerticalSpacer height={10} />
            <VariantTags project={props.project} />
          </ProjectSection>
        </Grid.Column>
        <Grid.Column width={4}>
          <ProjectSection label="Collaborators" editPath="collaborators">
            <ProjectCollaborators />
          </ProjectSection>
          <VerticalSpacer height={30} />
          <ProjectSection label="Gene Lists">
            <GeneLists />
          </ProjectSection>
        </Grid.Column>
      </Grid.Row>
      <Grid.Row>
        <Grid.Column width={16}>
          <SectionHeader>Families</SectionHeader>
          <FamilyTable
            headerStatus={headerStatus}
            exportUrls={exportUrls}
            showSearchLinks
            showVariantTags
            detailFields={FAMILY_DETAIL_FIELDS}
            noDetailFields={NO_DETAIL_FIELDS}
          />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  )
}

ProjectPageUI.propTypes = {
  project: PropTypes.object.isRequired,
  analysisStatusCounts: PropTypes.array,
  familyExportConfig: PropTypes.object,
  individualsExportConfig: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
  analysisStatusCounts: getAnalysisStatusCounts(state),
  familyExportConfig: getFamiliesExportConfig(state),
  individualsExportConfig: getIndividualsExportConfig(state),
})

export { ProjectPageUI as ProjectPageUIComponent }

export default connect(mapStateToProps)(ProjectPageUI)


import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Loader } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

import { getCurrentProject } from 'redux/selectors'
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
  getProjectDetailsIsLoading,
  getAnalysisStatusCounts,
  getFamiliesExportConfig,
  getIndividualsExportConfig,
  getSamplesExportConfig,
  getProjectAnalysisGroupsByGuid,
} from '../selectors'
import ProjectOverview from './ProjectOverview'
import AnalysisGroups from './AnalysisGroups'
import { UpdateAnalysisGroupButton } from './AnalysisGroupButtons'
import ProjectCollaborators, { AddProjectCollaboratorButton } from './ProjectCollaborators'
import { GeneLists, AddGeneListsButton } from './GeneLists'
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

const ProjectSectionComponent = ({ loading, label, children, editButton, linkPath, linkText, project }) => {
  return ([
    <SectionHeader key="header">{label}</SectionHeader>,
    <div key="content">
      {loading ? <Loader key="content" inline active /> : children}
    </div>,
    editButton && project.canEdit ? (
      <div key="edit">
        <VerticalSpacer height={15} />
        {editButton}
      </div>
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
  project: getCurrentProject(state),
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
  const exportUrls = [
    { name: 'Families', data: props.familyExportConfig },
    { name: 'Individuals', data: props.individualsExportConfig },
    { name: 'Samples', data: props.samplesExportConfig },
  ]

  return (
    <Grid stackable>
      <Grid.Row>
        <Grid.Column width={4}>
          {props.match.params.analysisGroupGuid ? null :
          <ProjectSection label="Analysis Groups" editButton={<UpdateAnalysisGroupButton />}>
            <AnalysisGroups />
          </ProjectSection>}
          <VerticalSpacer height={10} />
          <ProjectSection label="Gene Lists" editButton={<AddGeneListsButton project={props.project} />}>
            <GeneLists project={props.project} />
          </ProjectSection>
        </Grid.Column>
        <Grid.Column width={8}>
          <ProjectSection label="Overview">
            <ProjectOverview project={props.project} analysisGroupGuid={props.match.params.analysisGroupGuid} />
          </ProjectSection>
          <VerticalSpacer height={10} />
          <ProjectSection label="Variant Tags" linkPath="saved_variants" linkText="View All">
            <VariantTagTypeBar
              project={props.project}
              analysisGroup={props.analysisGroup}
              height={20}
              showAllPopupCategorie
            />
            <VerticalSpacer height={10} />
            <VariantTags project={props.project} analysisGroup={props.analysisGroup} />
          </ProjectSection>
        </Grid.Column>
        <Grid.Column width={4}>
          <ProjectSection label="Collaborators" editButton={<AddProjectCollaboratorButton />}>
            <ProjectCollaborators />
          </ProjectSection>
        </Grid.Column>
      </Grid.Row>
      <Grid.Row>
        <Grid.Column width={16}>
          <SectionHeader>Families</SectionHeader>
          <FamilyTable
            exportUrls={exportUrls}
            showVariantDetails
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
  analysisGroup: PropTypes.object,
  familyExportConfig: PropTypes.object,
  individualsExportConfig: PropTypes.object,
  samplesExportConfig: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  analysisGroup: getProjectAnalysisGroupsByGuid(state)[ownProps.match.params.analysisGroupGuid],
  analysisStatusCounts: getAnalysisStatusCounts(state, ownProps),
  familyExportConfig: getFamiliesExportConfig(state, ownProps),
  individualsExportConfig: getIndividualsExportConfig(state, ownProps),
  samplesExportConfig: getSamplesExportConfig(state, ownProps),
})

export { ProjectPageUI as ProjectPageUIComponent }

export default connect(mapStateToProps)(ProjectPageUI)


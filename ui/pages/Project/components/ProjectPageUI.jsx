import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Loader } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { SectionHeader } from 'shared/components/StyledComponents'
import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_DETAIL_FIELDS,
} from 'shared/utils/constants'
import {
  getCurrentProject,
  getProjectDetailsIsLoading,
  getAnalysisStatusCounts,
  getProjectOverviewIsLoading,
  getFamiliesLoading,
  getTagTypeCounts,
  getAnalysisGroupTagTypeCounts,
} from '../selectors'
import { loadProjectOverview } from '../reducers'
import ProjectOverview from './ProjectOverview'
import AnalysisGroups from './AnalysisGroups'
import { UpdateAnalysisGroupButton } from './AnalysisGroupButtons'
import ProjectCollaborators from './ProjectCollaborators'
import { GeneLists, AddGeneListsButton } from './GeneLists'
import FamilyTable from './FamilyTable/FamilyTable'
import VariantTags from './VariantTags'
import VariantTagTypeBar from './VariantTagTypeBar'

const ProjectSectionComponent = React.memo((
  { loading, label, children, editButton, linkPath, linkText, project, collaboratorEdit },
) => ([
  <SectionHeader key="header">{label}</SectionHeader>,
  <div key="content">
    {loading ? <Loader key="content" inline active /> : children}
  </div>,
  editButton && (project.canEdit || collaboratorEdit) ? (
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
]))

ProjectSectionComponent.propTypes = {
  loading: PropTypes.bool,
  label: PropTypes.string,
  children: PropTypes.node,
  editButton: PropTypes.node,
  linkPath: PropTypes.string,
  linkText: PropTypes.string,
  project: PropTypes.object,
  collaboratorEdit: PropTypes.bool,
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

const ProjectPageUI = React.memo(props => (
  <Grid stackable>
    <DataLoader load={props.load} loading={props.loading} content>
      <Grid.Row>
        <Grid.Column width={4}>
          {props.match.params.analysisGroupGuid ? null : (
            <ProjectSection label="Analysis Groups" editButton={<UpdateAnalysisGroupButton />}>
              <AnalysisGroups />
            </ProjectSection>
          )}
          <VerticalSpacer height={10} />
          <ProjectSection label="Gene Lists" editButton={<AddGeneListsButton project={props.project} />} collaboratorEdit>
            <GeneLists project={props.project} />
          </ProjectSection>
        </Grid.Column>
        <Grid.Column width={8}>
          <ProjectSection label="Overview">
            <ProjectOverview
              project={props.project}
              analysisGroupGuid={props.match.params.analysisGroupGuid}
              familiesLoading={props.familiesLoading}
            />
          </ProjectSection>
          <VerticalSpacer height={10} />
          <ProjectSection label="Variant Tags" linkPath="saved_variants" linkText="View All">
            <VariantTagTypeBar
              project={props.project}
              analysisGroupGuid={props.match.params.analysisGroupGuid}
              tagTypeCounts={props.tagTypeCounts}
              height={20}
              showAllPopupCategories
            />
            <VerticalSpacer height={10} />
            <VariantTags
              project={props.project}
              analysisGroupGuid={props.match.params.analysisGroupGuid}
              tagTypeCounts={props.tagTypeCounts}
            />
          </ProjectSection>
        </Grid.Column>
        <Grid.Column width={4}>
          <ProjectSection label="Collaborators">
            <ProjectCollaborators />
          </ProjectSection>
        </Grid.Column>
      </Grid.Row>
    </DataLoader>
    <Grid.Row>
      <Grid.Column width={16}>
        <SectionHeader>Families</SectionHeader>
        <FamilyTable
          showVariantDetails
          detailFields={FAMILY_DETAIL_FIELDS}
          noDetailFields={NO_DETAIL_FIELDS}
        />
      </Grid.Column>
    </Grid.Row>
  </Grid>
))

ProjectPageUI.propTypes = {
  project: PropTypes.object.isRequired,
  match: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
  familiesLoading: PropTypes.bool,
  tagTypeCounts: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  analysisStatusCounts: getAnalysisStatusCounts(state, ownProps),
  loading: getProjectOverviewIsLoading(state),
  familiesLoading: getFamiliesLoading(state),
  tagTypeCounts: ownProps.match.params.analysisGroupGuid ?
    getAnalysisGroupTagTypeCounts(state, ownProps) : getTagTypeCounts(state),
})

const mapDispatchToProps = {
  load: loadProjectOverview,
}

export { ProjectPageUI as ProjectPageUIComponent }

export default connect(mapStateToProps, mapDispatchToProps)(ProjectPageUI)

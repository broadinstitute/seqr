import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Icon, Popup } from 'semantic-ui-react'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import ListFieldView from 'shared/components/panel/view-fields/ListFieldView'
import { FAMILY_ANALYSIS_STATUS_LOOKUP } from 'shared/constants/familyAndIndividualConstants'
import ColoredIcon from 'shared/components/icons/ColoredIcon'
import { getProject, updateFamilies } from 'redux/rootReducer'

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateFamily: (values) => {
      dispatch(updateFamilies({ families: [{ familyGuid: ownProps.family.familyGuid, ...values }] }))
    },
  }
}


const AnalysisStatus = ({ family, project, canEdit }) => {
  const familyAnalysisStatus = (
    (family.analysisStatus && FAMILY_ANALYSIS_STATUS_LOOKUP[family.analysisStatus]) ?
      FAMILY_ANALYSIS_STATUS_LOOKUP[family.analysisStatus] :
      {}
  )
  return (
    <div style={{ whiteSpace: 'nowrap' }}>
      <div style={{ display: 'inline-block', padding: '5px 15px 5px 0px' }}><b>Analysis Status: </b></div>
      <Popup
        trigger={<ColoredIcon name="play" styleColor={familyAnalysisStatus.color} />}
        content={<div>Analysis Status:<br />{familyAnalysisStatus.name}</div>}
      />
      {familyAnalysisStatus.name}
      {canEdit && project.canEdit &&
        <a
          style={{ paddingLeft: '15px' }}
          href={`/project/${project.deprecatedProjectId}/family/${family.familyId}/edit`}
        >
          <Icon name="write" size="small" />
        </a>
      }
    </div>
  )
}

AnalysisStatus.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  canEdit: PropTypes.bool,
}

const BaseAnalysedBy = ({ family, updateFamily, canEdit }) =>
  <ListFieldView
    isEditable={canEdit}
    fieldName="Analysed By"
    values={family.analysedBy.map(analysedByObj => `${analysedByObj.user.display_name} (${analysedByObj.date_saved})`)}
    addItemUrl={`/api/family/${family.familyGuid}/update_analysed_by`}
    onItemAdded={updateFamily}
    confirmAddMessage="Are you sure you want to add that you analysed this family?"
  />

BaseAnalysedBy.propTypes = {
  family: PropTypes.object.isRequired,
  canEdit: PropTypes.bool,
  updateFamily: PropTypes.func,
}

const AnalysedBy = connect(null, mapDispatchToProps)(BaseAnalysedBy)

export const DESCRIPTION = 'description'
export const ANALYSIS_STATUS = 'analysisStatus'
export const ANALYSED_BY = 'analysedBy'
export const ANALYSIS_NOTES = 'analysisNotes'
export const ANALYSIS_SUMMARY = 'analysisSummary'
export const INTERNAL_NOTES = 'internalCaseReviewNotes'
export const INTERNAL_SUMMARY = 'internalCaseReviewSummary'

const fieldRenderDetails = {
  [DESCRIPTION]: { name: 'Family Description' },
  [ANALYSIS_STATUS]: { component: AnalysisStatus },
  [ANALYSED_BY]: { component: AnalysedBy },
  [ANALYSIS_NOTES]: { name: 'Analysis Notes' },
  [ANALYSIS_SUMMARY]: { name: 'Analysis Summary' },
  [INTERNAL_NOTES]: { name: 'Internal Notes', internal: true },
  [INTERNAL_SUMMARY]: { name: 'Internal Summary', internal: true },
}


const FamilyRow = ({ family, project, fields = [], updateFamily, showSearchLinks }) =>
  <Grid stackable>
    <Grid.Row>
      <Grid.Column width={3}>
        <span style={{ paddingLeft: '0px' }}>
          <b>
            Family: &nbsp;
            <a href={`/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
              {family.displayName}
            </a>
          </b>
          <br />
        </span>
        <br />
        <PedigreeImagePanel family={family} />
      </Grid.Column>

      <Grid.Column width={10}>
        {fields.map((field) => {
          const renderDetails = fieldRenderDetails[field.id]
          return renderDetails.component ?
            React.createElement(renderDetails.component, { key: field.id, family, project, ...field }) :
            <TextFieldView
              key={field.id}
              isEditable={project.canEdit && field.canEdit}
              isPrivate={renderDetails.internal}
              fieldName={renderDetails.name}
              fieldId={field.id}
              initialText={family[field.id]}
              textEditorId={`edit-${field.id}-${family.familyGuid}`}
              textEditorTitle={`${renderDetails.name} for Family ${family.displayName}`}
              textEditorSubmit={updateFamily}
            />
          },
        )}
        <br />
      </Grid.Column>
      {showSearchLinks &&
        <Grid.Column width={3}>
          <a
            style={{ display: 'block', padding: '5px 0px' }}
            href={`/project/${project.deprecatedProjectId}/family/${family.familyId}`}
          >
            Family Page
          </a>
          <a
            style={{ display: 'block', padding: '5px 0px' }}
            href={`/project/${project.deprecatedProjectId}/family/${family.familyId}/mendelian-variant-search`}
          >
            <Icon name="search" />Variant Search
          </a>
          {
            project.isMmeEnabled &&
            <a
              style={{ display: 'block', padding: '5px 0px' }}
              href={`/matchmaker/search/project/${project.deprecatedProjectId}/family/${family.familyId}`}
            >
              <Icon name="search" />Match Maker Exchange
            </a>
          }
        </Grid.Column>
      }
    </Grid.Row>
  </Grid>

export { FamilyRow as FamilyRowComponent }

FamilyRow.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  fields: PropTypes.array,
  showSearchLinks: PropTypes.bool,
  updateFamily: PropTypes.func,
}


const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(FamilyRow)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { getProject, updateFamiliesByGuid } from 'redux/utils/commonDataActionsAndSelectors'


const FamilyRow = props => (
  <Grid stackable style={{ width: '100%' }}>
    <Grid.Row style={{ paddingTop: '20px', paddingRight: '10px' }}>
      <Grid.Column width={3} style={{ maxWidth: '250px' }}>
        <span style={{ paddingLeft: '0px' }}>
          <b>
            Family: &nbsp;
            <a href={`/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}`}>
              {props.family.displayName}
            </a>
          </b>
          {/*
            (props.family.causalInheritanceMode && props.family.causalInheritanceMode !== 'unknown') ?
            `Inheritance: ${props.family.causalInheritanceMode}` :
            null
          */}
          <br />
        </span>
        <br />
        <PedigreeImagePanel family={props.family} />
      </Grid.Column>

      <Grid.Column width={13} style={{ maxWidth: '950px' }}>
        <TextFieldView
          isEditable
          fieldName="Family Description"
          initialText={props.family.description}
          textEditorId={`editDescription-${props.family.familyGuid}`}
          textEditorTitle={`Description for Family ${props.family.displayName}`}
          textEditorSubmitUrl={`/api/family/${props.family.familyGuid}/update/description`}
        />
        <TextFieldView
          fieldName="Analysis Notes"
          initialText={props.family.analysisNotes}
        />
        <TextFieldView
          fieldName="Analysis Summary"
          initialText={props.family.analysisSummary}
        />
        <div style={{ maxWidth: '800px' }}>
          <TextFieldView
            isPrivate
            isEditable
            fieldName="Internal Notes"
            initialText={props.family.internalCaseReviewNotes}
            textEditorId={`editInternalNotes-${props.family.familyGuid}`}
            textEditorTitle={`Internal Notes for Family ${props.family.displayName}`}
            textEditorSubmitUrl={`/api/family/${props.family.familyGuid}/save_internal_case_review_notes`}
          />
          <TextFieldView
            isPrivate
            isEditable
            fieldName="Internal Summary"
            initialText={props.family.internalCaseReviewSummary}
            textEditorId={`editInternalSummary-${props.family.familyGuid}`}
            textEditorTitle={`Internal Summary for Family ${props.family.displayName}`}
            textEditorSubmitUrl={`/api/family/${props.family.familyGuid}/save_internal_case_review_summary`}
          />
        </div><br />
      </Grid.Column>
    </Grid.Row>
  </Grid>
)

export { FamilyRow as FamilyRowComponent }

FamilyRow.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
}


const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = {
  updateFamiliesByGuid,
}

export default connect(mapStateToProps, mapDispatchToProps)(FamilyRow)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'

import PedigreeImagePanel from 'shared/components/panel/pedigree-image/PedigreeImagePanel'
import TextFieldView from 'shared/components/panel/text-field-view/TextFieldView'
import { getProject, updateFamiliesByGuid } from '../../../reducers/rootReducer'
import { EDIT_FAMILY_INFO_MODAL_ID } from './EditFamilyInfoModal'

const FamilyRow = props => (
  <Grid stackable style={{ width: '100%' }}>
    <Grid.Row style={{ paddingTop: '20px', paddingRight: '10px' }}>
      <Grid.Column width={3}>
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

      <Grid.Column width={13}>
        <TextFieldView
          isRichText
          fieldName="Family Description"
          initialText={props.family.description}
        />
        <TextFieldView
          isRichText
          fieldName="Analysis Notes"
          initialText={props.family.analysisNotes}
        />
        <TextFieldView
          isRichText
          fieldName="Analysis Summary"
          initialText={props.family.analysisSummary}
        />
        <TextFieldView
          isRichText
          isPrivate
          isEditable
          fieldName="Internal Notes"
          initialText={props.family.internalCaseReviewNotes}
          textEditorId={EDIT_FAMILY_INFO_MODAL_ID}
          textEditorTitle={`Internal Notes: ${props.family.displayName}`}
          textEditorSubmitUrl={`/api/family/${props.family.familyGuid}/save_internal_case_review_notes`}
        />
        <TextFieldView
          isRichText
          isPrivate
          isEditable
          fieldName="Internal Summary"
          initialText={props.family.internalCaseReviewSummary}
          textEditorId={EDIT_FAMILY_INFO_MODAL_ID}
          textEditorTitle={`Internal Summary: ${props.family.displayName}`}
          textEditorSubmitUrl={`/api/family/${props.family.familyGuid}/save_internal_case_review_summary`}
        /><br />
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

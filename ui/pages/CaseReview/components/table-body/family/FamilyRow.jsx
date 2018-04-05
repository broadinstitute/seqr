import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { getProject, updateFamilies } from 'redux/rootReducer'


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
          fieldId="description"
          initialText={props.family.description}
          textEditorId={`editDescription-${props.family.familyGuid}`}
          textEditorTitle={`Description for Family ${props.family.displayName}`}
          textEditorSubmit={props.updateFamily}
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
            fieldId="internalCaseReviewNotes"
            initialText={props.family.internalCaseReviewNotes}
            textEditorId={`editInternalNotes-${props.family.familyGuid}`}
            textEditorTitle={`Internal Notes for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
          />
          <TextFieldView
            isPrivate
            isEditable
            fieldName="Internal Summary"
            fieldId="internalCaseReviewSummary"
            initialText={props.family.internalCaseReviewSummary}
            textEditorId={`editInternalSummary-${props.family.familyGuid}`}
            textEditorTitle={`Internal Summary for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
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
  updateFamily: PropTypes.func,
}


const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateFamily: (values) => {
      dispatch(updateFamilies({ families: [{ familyGuid: ownProps.family.familyGuid, ...values }] }))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(FamilyRow)

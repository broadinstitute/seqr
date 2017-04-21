import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Grid } from 'semantic-ui-react'

import FamilyInfoField from './FamilyInfoField'
import PedigreeImage from './PedigreeImage'
import { getProject, updateFamiliesByGuid } from '../../../reducers/rootReducer'

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
          {
            (props.family.causalInheritanceMode && props.family.causalInheritanceMode !== 'unknown') ?
            `Inheritance: ${props.family.causalInheritanceMode}` :
            null
          }
          <br />
        </span>
        <br />
        <PedigreeImage family={props.family} />
      </Grid.Column>

      <Grid.Column width={13}>
        <FamilyInfoField
          fieldName="Family Description"
          initialText={props.family.description}
        />
        <FamilyInfoField
          fieldName="Analysis Notes"
          initialText={props.family.analysisNotes}
        />
        <FamilyInfoField
          fieldName="Analysis Summary"
          initialText={props.family.analysisSummary}
        />
        <FamilyInfoField
          isPrivate
          isEditable
          fieldName="Internal Notes"
          initialText={props.family.internalCaseReviewNotes}
          editFamilyInfoModalTitle={`Family ${props.family.displayName}: Internal Notes`}
          editFamilyInfoModalSubmitUrl={`/api/family/${props.family.familyGuid}/save_internal_case_review_notes`}
        />
        <FamilyInfoField
          isPrivate
          isEditable
          fieldName="Internal Summary"
          initialText={props.family.internalCaseReviewSummary}
          editFamilyInfoModalTitle={`Family ${props.family.displayName}: Internal Summary`}
          editFamilyInfoModalSubmitUrl={`/api/family/${props.family.familyGuid}/save_internal_case_review_summary`}
        /><br />
      </Grid.Column>
    </Grid.Row>
  </Grid>
)

export { FamilyRow as FamilyRowComponent }

FamilyRow.propTypes = {
  project: React.PropTypes.object.isRequired,
  family: React.PropTypes.object.isRequired,
}


const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({
  updateFamiliesByGuid,
}, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(FamilyRow)

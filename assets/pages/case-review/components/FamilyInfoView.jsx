import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import FamilyInfoField from './FamilyInfoField'
import FamilyInfoEditableField from './FamilyInfoEditableField'
import { updateInternalCaseReviewNotes, updateInternalCaseReviewSummary } from '../reducers/rootReducer'


class FamilyInfoView extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    updateInternalCaseReviewNotes: React.PropTypes.func.isRequired,
    updateInternalCaseReviewSummary: React.PropTypes.func.isRequired,
  }

  static infoDivStyle = {
    paddingLeft: '22px',
    maxWidth: '550px',
    wordWrap: 'break-word',
  }

  render() {
    const {
      project,
      family,
    } = this.props

    return <span>
      <FamilyInfoField
        initialText={family.shortDescription}
        label="Family Description"
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoField
        initialText={family.aboutFamilyContent}
        label="Analysis Notes"
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoField
        initialText={family.analysisSummaryContent}
        label="Analysis Summary"
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoEditableField
        familyId={family.familyId}
        isPrivate
        label="Internal Notes"
        initialText={family.internalCaseReviewNotes}
        submitUrl={`/api/project/${project.projectGuid}/family/${family.familyGuid}/save_internal_case_review_notes`}
        onSave={(response, savedJson) => { this.props.updateInternalCaseReviewNotes(family.familyId, savedJson.form) }}
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoEditableField
        familyId={family.familyId}
        isPrivate
        label="Internal Summary"
        initialText={family.internalCaseReviewSummary}
        submitUrl={`/api/project/${project.projectGuid}/family/${family.familyGuid}/save_internal_case_review_summary`}
        onSave={(response, savedJson) => this.props.updateInternalCaseReviewSummary(family.familyId, savedJson.form)}
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
    </span>
  }
}

const mapStateToProps = state => state

const mapDispatchToProps = dispatch => bindActionCreators({
  updateInternalCaseReviewNotes,
  updateInternalCaseReviewSummary,
}, dispatch)

// wrap presentational components in a container so that redux state is passed in as props
const FamilyInfoViewWrapper = connect(mapStateToProps, mapDispatchToProps)(FamilyInfoView)

export default FamilyInfoViewWrapper

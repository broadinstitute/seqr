import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import FamilyInfoField from './FamilyInfoField'
import FamilyInfoEditableField from './FamilyInfoEditableField'
import { updateFamiliesByGuid } from '../reducers/rootReducer'


class FamilyInfoView extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    updateFamiliesByGuid: React.PropTypes.func.isRequired,
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
        initialText={family.description}
        label="Family Description"
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoField
        initialText={family.analysisNotes}
        label="Analysis Notes"
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoField
        initialText={family.analysisSummary}
        label="Analysis Summary"
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoEditableField
        displayName={family.displayName}
        isPrivate
        label="Internal Notes"
        initialText={family.internalCaseReviewNotes}
        submitUrl={`/api/project/${project.projectGuid}/family/${family.familyGuid}/save_internal_case_review_notes`}
        onSave={responseJson => this.props.updateFamiliesByGuid(responseJson)}
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
      <FamilyInfoEditableField
        displayName={family.displayName}
        isPrivate
        label="Internal Summary"
        initialText={family.internalCaseReviewSummary}
        submitUrl={`/api/project/${project.projectGuid}/family/${family.familyGuid}/save_internal_case_review_summary`}
        onSave={responseJson => this.props.updateFamiliesByGuid(responseJson)}
        infoDivStyle={FamilyInfoView.infoDivStyle}
      />
    </span>
  }
}

const mapStateToProps = state => state

const mapDispatchToProps = dispatch => bindActionCreators({
  updateFamiliesByGuid,
}, dispatch)

// wrap presentational components in a container so that redux state is passed in as props
const FamilyInfoViewWrapper = connect(mapStateToProps, mapDispatchToProps)(FamilyInfoView)

export default FamilyInfoViewWrapper

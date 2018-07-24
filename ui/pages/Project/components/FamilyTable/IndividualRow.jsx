import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Popup, Icon } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import DispatchRequestButton from 'shared/components/buttons/DispatchRequestButton'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import PhenotipsDataPanel from 'shared/components/panel/view-phenotips-info/PhenotipsDataPanel'
import Sample from 'shared/components/panel/sample'
import { FamilyLayout } from 'shared/components/panel/family'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'

import { updateIndividual } from 'redux/rootReducer'
import { getUser, getMatchmakerSubmissions } from 'redux/selectors'
import { deleteMmePatient as dispatchDeleteMmePatient } from 'pages/Project/reducers'
import { getProject, getProjectSamplesByGuid } from 'pages/Project/selectors'
import { SAMPLE_STATUS_LOADED, DATASET_TYPE_VARIANT_CALLS } from 'shared/utils/constants'
import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_NOT_IN_REVIEW,
  CASE_REVIEW_STATUS_OPT_LOOKUP,
} from '../../constants'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'


const Detail = styled.div`
  display: inline-block;
  padding: 5px 0 5px 5px;
  font-size: 11px;
  font-weight: 500;
  color: #999999;
`

const ColoredSpan = styled.span`
  color: ${props => props.color}
`

const CaseReviewDropdownContainer = styled.div`
  float: right;
  width: 220px;
`

const SpacedLabel = styled(Label)`
  margin-top: 5px !important;
`

const CaseReviewStatus = ({ individual }) =>
  <CaseReviewDropdownContainer>
    <CaseReviewStatusDropdown individual={individual} />
    {
      individual.caseReviewStatusLastModifiedDate ? (
        <Detail>
          CHANGED ON {new Date(individual.caseReviewStatusLastModifiedDate).toLocaleDateString()}
          { individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}` }
        </Detail>
      ) : null
    }
  </CaseReviewDropdownContainer>

CaseReviewStatus.propTypes = {
  individual: PropTypes.object.isRequired,
}

const DataDetails = ({ loadedSamples, matchmakerSubmission, deleteMmePatient }) =>
  <div>
    {loadedSamples.map((sample, i) =>
      <div key={sample.sampleGuid}>
        <Sample loadedSample={sample} isOutdated={i !== 0} />
      </div>,
    )}
    {matchmakerSubmission && (
      matchmakerSubmission.deletion ? (
        <Popup
          key={matchmakerSubmission.submissionDate}
          flowing
          trigger={
            <SpacedLabel color="red" size="small">
              Removed from MME: {new Date(matchmakerSubmission.deletion.date).toLocaleDateString()}
            </SpacedLabel>
          }
          content={
            <div>
              <b>Removed By: </b>{matchmakerSubmission.deletion.by}<br />
              <b>Originally Submitted: </b>{new Date(matchmakerSubmission.submissionDate).toLocaleDateString()}
            </div>
          }
        />
      ) : (
        <div key={matchmakerSubmission.submissionDate}>
          <SpacedLabel color="violet" size="small">
            Submitted to MME: {new Date(matchmakerSubmission.submissionDate).toLocaleDateString()}
          </SpacedLabel>
          <DispatchRequestButton
            buttonContent={<Icon name="trash" />}
            confirmDialog="Are you sure you want to remove the patient from MatchMaker Exchange?"
            onSubmit={deleteMmePatient}
          />
        </div>
      )
    )
  }
  </div>

DataDetails.propTypes = {
  matchmakerSubmission: PropTypes.object,
  loadedSamples: PropTypes.array,
  deleteMmePatient: PropTypes.func,
}

class IndividualRow extends React.Component
{
  static propTypes = {
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    samplesByGuid: PropTypes.object.isRequired,
    matchmakerSubmission: PropTypes.object,
    updateIndividual: PropTypes.func,
    deleteMmePatient: PropTypes.func,
    editCaseReview: PropTypes.bool,
  }

  render() {
    const { user, project, family, individual, editCaseReview, matchmakerSubmission, deleteMmePatient } = this.props

    const { individualId, displayName, paternalId, maternalId, sex, affected, createdDate } = individual

    const caseReviewStatusOpt = CASE_REVIEW_STATUS_OPT_LOOKUP[individual.caseReviewStatus]

    let loadedSamples = individual.sampleGuids.map(
      sampleGuid => this.props.samplesByGuid[sampleGuid],
    ).filter(s =>
      s.datasetType === DATASET_TYPE_VARIANT_CALLS &&
      s.sampleStatus === SAMPLE_STATUS_LOADED,
    )
    loadedSamples = orderBy(loadedSamples, [s => s.loadedDate], 'desc')
    // only show first and latest samples
    loadedSamples.splice(1, loadedSamples.length - 2)

    const leftContent =
      <div>
        <div>
          <PedigreeIcon sex={sex} affected={affected} />
          &nbsp;
          {displayName || individualId}
        </div>
        <div>
          {
            (!family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
              <Detail>
                child of &nbsp;
                <i>{(paternalId && maternalId) ? `${paternalId} and ${maternalId}` : (paternalId || maternalId) }</i>
                <br />
              </Detail>
            ) : null
          }
          <Detail>
            ADDED {new Date(createdDate).toLocaleDateString().toUpperCase()}
          </Detail>
        </div>
      </div>

    const rightContent = editCaseReview ?
      <CaseReviewStatus individual={individual} /> :
      <DataDetails loadedSamples={loadedSamples} matchmakerSubmission={matchmakerSubmission} deleteMmePatient={deleteMmePatient} />

    let fields = []
    if (editCaseReview ||
      (individual.caseReviewStatus && individual.caseReviewStatus !== CASE_REVIEW_STATUS_NOT_IN_REVIEW) ||
      (individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED)) {
      fields.push({
        content: (
          <div key="case review">
            {!editCaseReview &&
              <span>
                <b>Case Review - Status:</b>
                <HorizontalSpacer width={15} />
                <ColoredSpan color={caseReviewStatusOpt ? caseReviewStatusOpt.color : 'black'}>
                  <b>{caseReviewStatusOpt ? caseReviewStatusOpt.name : individual.caseReviewStatus}</b>
                </ColoredSpan>
              </span>
            }
            {!editCaseReview && individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED && <br />}
            <TextFieldView
              isVisible={
                individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED
                || (editCaseReview && individual.caseReviewDiscussion) || false
              }
              fieldName={editCaseReview ? 'Case Review Discussion' : 'Discussion'}
              field="caseReviewDiscussion"
              idField="individualGuid"
              initialValues={individual}
              modalTitle={`Case Review Discussion for Individual ${individual.individualId}`}
              onSubmit={this.props.updateIndividual}
            />
            <VerticalSpacer height={10} />
          </div>
        ),
      })
    }
    fields = fields.concat([
      {
        content: (
          <TextFieldView
            key="notes"
            isEditable={(user.is_staff || project.canEdit) && !editCaseReview}
            fieldName="Individual Notes"
            field="notes"
            idField="individualGuid"
            initialValues={individual}
            modalTitle={`Notes for Individual ${individual.individualId}`}
            onSubmit={this.props.updateIndividual}
          />
        ),
      },
      {
        content: (
          <PhenotipsDataPanel
            key="phenotips"
            individual={individual}
            showDetails
            showEditPhenotipsLink={project.canEdit && !editCaseReview}
          />
        ),
      },
    ])

    return (
      <FamilyLayout
        fields={fields}
        fieldDisplay={field => field.content}
        leftContent={leftContent}
        rightContent={rightContent}
      />
    )
  }
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = (state, ownProps) => ({
  user: getUser(state),
  project: getProject(state),
  samplesByGuid: getProjectSamplesByGuid(state),
  matchmakerSubmission: getMatchmakerSubmissions(state)[ownProps.family.projectGuid][ownProps.individual.individualId],
})


const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateIndividual: (values) => {
      return dispatch(updateIndividual(values))
    },
    deleteMmePatient: () => {
      return dispatch(dispatchDeleteMmePatient(ownProps.individual))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

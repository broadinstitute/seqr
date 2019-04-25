import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Popup, Icon } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import DispatchRequestButton from 'shared/components/buttons/DispatchRequestButton'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import PhenotipsDataPanel from 'shared/components/panel/PhenotipsDataPanel'
import Sample from 'shared/components/panel/sample'
import { FamilyLayout } from 'shared/components/panel/family'
import { ColoredIcon } from 'shared/components/StyledComponents'

import { updateIndividual } from 'redux/rootReducer'
import { getSamplesByGuid } from 'redux/selectors'
import { getProject } from 'pages/Project/selectors'
import { deleteMmePatient } from 'pages/Project/reducers'
import { SAMPLE_STATUS_LOADED, DATASET_TYPE_VARIANT_CALLS } from 'shared/utils/constants'
import { CASE_REVIEW_STATUS_MORE_INFO_NEEDED, CASE_REVIEW_STATUS_OPTIONS } from '../../constants'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'


const Detail = styled.div`
  display: inline-block;
  padding: 5px 0 5px 5px;
  font-size: 11px;
  font-weight: 500;
  color: #999999;
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

const DataDetails = ({ loadedSamples, individual, deleteIndividualMmePatient }) =>
  <div>
    {loadedSamples.map((sample, i) =>
      <div key={sample.sampleGuid}>
        <Sample loadedSample={sample} isOutdated={i !== 0} />
      </div>,
    )}
    {individual.mmeSubmittedDate && (
      individual.mmeDeletedDate ? (
        <Popup
          key={individual.mmeSubmittedDate}
          flowing
          trigger={
            <SpacedLabel color="red" size="small">
              Removed from MME: {new Date(individual.mmeDeletedDate).toLocaleDateString()}
            </SpacedLabel>
          }
          content={
            <div>
              <b>Originally Submitted: </b>{new Date(individual.mmeSubmittedDate).toLocaleDateString()}
            </div>
          }
        />
      ) : (
        <div key={individual.mmeSubmittedDate}>
          <SpacedLabel color="violet" size="small">
            Submitted to MME: {new Date(individual.mmeSubmittedDate).toLocaleDateString()}
          </SpacedLabel>
          <DispatchRequestButton
            buttonContent={<Icon name="trash" />}
            confirmDialog="Are you sure you want to remove the patient from MatchMaker Exchange?"
            onSubmit={deleteIndividualMmePatient}
          />
        </div>
      )
    )
  }
  </div>

DataDetails.propTypes = {
  individual: PropTypes.object,
  loadedSamples: PropTypes.array,
  deleteIndividualMmePatient: PropTypes.func,
}

class IndividualRow extends React.Component
{
  static propTypes = {
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    samplesByGuid: PropTypes.object.isRequired,
    updateIndividual: PropTypes.func,
    deleteIndividualMmePatient: PropTypes.func,
    editCaseReview: PropTypes.bool,
  }

  render() {
    const { project, family, individual, editCaseReview, deleteIndividualMmePatient } = this.props

    const { displayName, paternalId, maternalId, sex, affected, createdDate, sampleGuids, caseReviewStatus, caseReviewDiscussion } = individual

    let loadedSamples = sampleGuids.map(
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
          <PedigreeIcon sex={sex} affected={affected} /> {displayName}
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
      <DataDetails loadedSamples={loadedSamples} individual={individual} deleteIndividualMmePatient={deleteIndividualMmePatient} />

    const fields = [
      {
        content: (
          <OptionFieldView
            key="caseReviewStatus"
            isVisible={!editCaseReview}
            fieldName="Case Review Status"
            field="caseReviewStatus"
            idField="individualGuid"
            initialValues={individual}
            tagOptions={CASE_REVIEW_STATUS_OPTIONS}
            tagAnnotation={value => <ColoredIcon name="stop" color={value.color} />}
          />
        ),
      },
      {
        content: (
          <TextFieldView
            key="discussion"
            isVisible={
              caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED
              || (editCaseReview && caseReviewDiscussion) || false
            }
            fieldName={editCaseReview ? 'Case Review Discussion' : 'Discussion'}
            field="caseReviewDiscussion"
            idField="individualGuid"
            initialValues={individual}
          />
        ),
      },
      {
        content: (
          <TextFieldView
            key="notes"
            isEditable={project.canEdit}
            fieldName="Individual Notes"
            field="notes"
            idField="individualGuid"
            initialValues={individual}
            modalTitle={`Notes for Individual ${displayName}`}
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
            showEditPhenotipsLink={project.canEdit}
          />
        ),
      },
    ]

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

const mapStateToProps = state => ({
  project: getProject(state),
  samplesByGuid: getSamplesByGuid(state),
})


const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateIndividual: (values) => {
      return dispatch(updateIndividual(values))
    },
    deleteIndividualMmePatient: () => {
      return dispatch(deleteMmePatient(ownProps.individual))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

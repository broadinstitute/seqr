import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Grid, Popup, Icon } from 'semantic-ui-react'
import Timeago from 'timeago.js'
import orderBy from 'lodash/orderBy'

import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import PhenotipsDataPanel from 'shared/components/panel/view-phenotips-info/PhenotipsDataPanel'

import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_NOT_IN_REVIEW,
  CASE_REVIEW_STATUS_OPT_LOOKUP,
} from 'shared/constants/caseReviewConstants'

import {
  ANALYSIS_TYPE_VARIANT_CALLS,
} from 'shared/constants/datasetAndSampleConstants'

import { getUser, getProject, updateIndividual } from 'redux/rootReducer'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { getProjectSamples, getProjectDatasets } from '../../utils/selectors'
import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'

import {
  getShowDetails,
} from '../../reducers'

const Detail = styled.span`
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

class IndividualRow extends React.Component
{
  static propTypes = {
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    showDetails: PropTypes.bool.isRequired,
    samples: PropTypes.array.isRequired,
    datasets: PropTypes.array.isRequired,
    updateIndividual: PropTypes.func,
    editCaseReview: PropTypes.bool,
  }

  render() {
    const { user, project, family, individual, showDetails, editCaseReview } = this.props

    const { individualId, displayName, paternalId, maternalId, sex, affected, createdDate } = individual

    const caseReviewStatusOpt = CASE_REVIEW_STATUS_OPT_LOOKUP[individual.caseReviewStatus]

    const sampleDetails = this.props.samples.filter(s => s.individualGuid === individual.individualGuid).map((sample) => {
      let loadedVariantCallDatasets = this.props.datasets
        .filter(dataset => (
          dataset.sampleGuids.includes(sample.sampleGuid) &&
          dataset.analysisType === ANALYSIS_TYPE_VARIANT_CALLS &&
          dataset.isLoaded
        ))

      loadedVariantCallDatasets = orderBy(loadedVariantCallDatasets, [d => d.loadedDate], 'desc')

      return (
        <div key={sample.sampleGuid}>
          {
            <Popup
              trigger={<Icon size="small" name="circle" color={loadedVariantCallDatasets.length > 0 ? 'green' : 'red'} />}
              content={loadedVariantCallDatasets.length > 0 ? 'data has been loaded' : 'no data available'}
              position="left center"
            />
          }
          <span><HorizontalSpacer width={8} /><b>{sample.sampleType}</b></span>
          {
            loadedVariantCallDatasets.length > 0 &&
            <Detail>
              LOADED {new Timeago().format(loadedVariantCallDatasets[0].loadedDate).toUpperCase()}
            </Detail>
          }
        </div>
      )
    })

    const individualRow = (
      <Grid stackable>
        <Grid.Row>
          <Grid.Column width={3}>
            <span>
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
                {
                  showDetails ? (
                    <Detail>
                      ADDED {new Timeago().format(createdDate).toUpperCase()}
                    </Detail>
                  ) : null
                }
              </div>
            </span>
          </Grid.Column>
          <Grid.Column width={10}>
            {
              ((showDetails && editCaseReview) ||
              (showDetails && individual.caseReviewStatus && individual.caseReviewStatus !== CASE_REVIEW_STATUS_NOT_IN_REVIEW) ||
              (individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED)) ?
                <div>
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
                    isEditable={user.is_staff || project.canEdit}
                    fieldName={editCaseReview ? 'Case Review Discussion' : 'Discussion'}
                    fieldId="caseReviewDiscussion"
                    initialText={individual.caseReviewDiscussion}
                    textEditorId={`editCaseReviewDiscussion-${individual.individualGuid}`}
                    textEditorTitle={`Case Review Discussion for Individual ${individual.individualId}`}
                    textEditorSubmit={this.props.updateIndividual}
                  />
                  <VerticalSpacer height={10} />
                </div>
                : null
            }
            {
              showDetails ?
                <div>
                  <TextFieldView
                    isEditable={(user.is_staff || project.canEdit) && !editCaseReview}
                    fieldName="Individual Notes"
                    fieldId="notes"
                    initialText={individual.notes}
                    textEditorId={`editNotes-${individual.individualGuid}`}
                    textEditorTitle={`Notes for Individual ${individual.individualId}`}
                    textEditorSubmit={this.props.updateIndividual}
                  />
                  <VerticalSpacer height={10} />
                </div>
                : null
            }
            <PhenotipsDataPanel
              project={project}
              individual={individual}
              showDetails={showDetails}
              showEditPhenotipsLink={project.canEdit && !editCaseReview}
            />
          </Grid.Column>
          <Grid.Column width={3}>
            {
              editCaseReview ?
                <CaseReviewDropdownContainer>
                  <CaseReviewStatusDropdown individual={individual} />
                  {
                    showDetails && individual.caseReviewStatusLastModifiedDate ? (
                      <Detail>
                        <HorizontalSpacer width={5} />
                        CHANGED {new Timeago().format(individual.caseReviewStatusLastModifiedDate).toUpperCase()}
                        { individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}` }
                      </Detail>
                    ) : null
                  }
                </CaseReviewDropdownContainer> : sampleDetails
            }
          </Grid.Column>
        </Grid.Row>
      </Grid>)

    return individualRow
  }
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
  showDetails: getShowDetails(state),
  samples: getProjectSamples(state),
  datasets: getProjectDatasets(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateIndividual: (values) => {
      dispatch(updateIndividual(ownProps.individual.individualGuid, values))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

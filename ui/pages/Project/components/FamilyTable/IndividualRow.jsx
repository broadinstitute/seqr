import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Grid, Popup, Icon } from 'semantic-ui-react'
import Timeago from 'timeago.js'
import orderBy from 'lodash/orderBy'

import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import PhenotipsDataPanel from 'shared/components/panel/view-phenotips-info/PhenotipsDataPanel'

import { getUser, updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_NOT_IN_REVIEW,
  CASE_REVIEW_STATUS_OPT_LOOKUP,
  ANALYSIS_TYPE_VARIANT_CALLS,
} from '../../constants'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'

import {
  getShowDetails, getProject, getProjectSamples, getProjectDatasets,
} from '../../reducers'

const detailsStyle = {
  padding: '5px 0 5px 5px',
  fontSize: '11px',
  fontWeight: '500',
  color: '#999999',
}

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
          <span style={{ marginLeft: '8px' }}><b>{sample.sampleType}</b></span>
          {
            loadedVariantCallDatasets.length > 0 &&
            <span style={detailsStyle}>
              LOADED {new Timeago().format(loadedVariantCallDatasets[0].loadedDate).toUpperCase()}
            </span>
          }
        </div>
      )
    })

    const individualRow = (
      <Grid stackable style={{ width: '100%' }}>
        <Grid.Row style={{ padding: '0px' }}>
          <Grid.Column width={3} style={{ maxWidth: '250px', padding: '0px 0px 15px 15px' }}>
            <span>
              <div style={{ display: 'block', verticalAlign: 'top', whiteSpace: 'nowrap' }} >
                <PedigreeIcon style={{ fontSize: '13px' }} sex={sex} affected={affected} />
                &nbsp;
                {displayName || individualId}
              </div>
              <div style={{ display: 'block' }} >
                {
                  (!family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
                    <div style={detailsStyle}>
                      child of &nbsp;
                      <i>{(paternalId && maternalId) ? `${paternalId} and ${maternalId}` : (paternalId || maternalId) }</i>
                      <br />
                    </div>
                  ) : null
                }
                {
                  showDetails ? (
                    <div style={detailsStyle}>
                      ADDED {new Timeago().format(createdDate).toUpperCase()}
                    </div>
                    ) : null
                }
              </div>
            </span>
          </Grid.Column>
          <Grid.Column width={10} style={{ maxWidth: '950px', padding: '0px 0px 15px 15px' }}>
            {
              ((showDetails && editCaseReview) ||
              (showDetails && individual.caseReviewStatus && individual.caseReviewStatus !== CASE_REVIEW_STATUS_NOT_IN_REVIEW) ||
              (individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED)) ?
                <div style={{ padding: '0px 0px 10px 0px' }}>
                  {!editCaseReview &&
                    <span style={{ paddingRight: '10px' }}>
                      <b>Case Review - Status:</b>
                      <span style={{ marginLeft: '15px', color: caseReviewStatusOpt ? caseReviewStatusOpt.color : 'black' }}>
                        <b>{caseReviewStatusOpt ? caseReviewStatusOpt.name : individual.caseReviewStatus}</b>
                      </span>
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
                    initialValues={individual}
                    textEditorId={`editCaseReviewDiscussion-${individual.individualGuid}`}
                    textEditorTitle={`Case Review Discussion for Individual ${individual.individualId}`}
                    textEditorSubmit={this.props.updateIndividual}
                  />
                </div>
                : null
            }
            {
              showDetails ?
                <div style={{ padding: '0px 0px 10px 0px' }}>
                  {
                    <TextFieldView
                      isEditable={(user.is_staff || project.canEdit) && !editCaseReview}
                      fieldName="Individual Notes"
                      fieldId="notes"
                      initialValues={individual}
                      textEditorId={`editNotes-${individual.individualGuid}`}
                      textEditorTitle={`Notes for Individual ${individual.individualId}`}
                      textEditorSubmit={this.props.updateIndividual}
                    />
                  }
                </div>
                : null
            }
            <PhenotipsDataPanel
              individual={individual}
              showDetails={showDetails}
              showEditPhenotipsLink={project.canEdit && !editCaseReview}
            />
          </Grid.Column>
          <Grid.Column width={3}>
            {
              editCaseReview ?
                <div style={{ float: 'right', width: '220px' }}>
                  <CaseReviewStatusDropdown individual={individual} />
                  {
                    showDetails && individual.caseReviewStatusLastModifiedDate ? (
                      <div style={{ ...detailsStyle, marginLeft: '2px' }}>
                        CHANGED {new Timeago().format(individual.caseReviewStatusLastModifiedDate).toUpperCase()}
                        { individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}` }
                      </div>
                    ) : null
                  }
                </div> : sampleDetails
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

const mapDispatchToProps = {
  updateIndividual,
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

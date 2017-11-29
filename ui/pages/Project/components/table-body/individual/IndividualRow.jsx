import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Grid, Popup, Icon } from 'semantic-ui-react'
import Timeago from 'timeago.js'
import orderBy from 'lodash/orderBy'

import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import TextFieldView from 'shared/components/panel/text-field-view/TextFieldView'
import PhenotipsDataPanel from 'shared/components/panel/phenotips-view/PhenotipsDataPanel'

import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_NOT_IN_REVIEW,
  CASE_REVIEW_STATUS_OPT_LOOKUP,
} from 'shared/constants/caseReviewConstants'

import {
  ANALYSIS_TYPE_VARIANT_CALLS,
} from 'shared/constants/datasetAndSampleConstants'

import { getUser, getProject, getSamplesByGuid, getDatasetsByGuid } from 'shared/utils/commonSelectors'

import { EDIT_INDIVIDUAL_INFO_MODAL_ID } from './EditIndividualInfoModal'


import {
  getShowDetails,
} from '../../../reducers/rootReducer'

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
    samplesByGuid: PropTypes.object.isRequired,
    datasetsByGuid: PropTypes.object.isRequired,
  }

  render() {
    const { user, project, family, individual, showDetails } = this.props

    const { individualId, displayName, paternalId, maternalId, sex, affected, createdDate } = individual

    const caseReviewStatusOpt = CASE_REVIEW_STATUS_OPT_LOOKUP[individual.caseReviewStatus]

    return (
      <Grid stackable style={{ width: '100%' }}>
        <Grid.Row style={{ padding: '0px' }}>
          <Grid.Column width={3} style={{ padding: '0px 0px 15px 15px' }}>
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
                      <i>{(paternalId && maternalId) ? `${paternalId}, ${maternalId}` : (paternalId || maternalId) }</i>
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
          <Grid.Column width={10}>
            {
              ((showDetails && individual.caseReviewStatus && individual.caseReviewStatus !== CASE_REVIEW_STATUS_NOT_IN_REVIEW) ||
              (individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED)) ?
                <div style={{ padding: '0px 0px 10px 0px' }}>
                  <span style={{ paddingRight: '10px' }}>
                    <b>Case Review - Status:</b>
                    <span style={{ marginLeft: '15px', color: caseReviewStatusOpt ? caseReviewStatusOpt.color : 'black' }}>
                      <b>{caseReviewStatusOpt ? caseReviewStatusOpt.name : individual.caseReviewStatus}</b>
                    </span>
                  </span>
                  {
                    <TextFieldView
                      isVisible={individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED}
                      isEditable={user.is_staff || user.canEdit}
                      fieldName="➙ Discussion"
                      initialText={individual.caseReviewDiscussion}
                      textEditorId={EDIT_INDIVIDUAL_INFO_MODAL_ID}
                      textEditorTitle={`Case Review Discussion for Individual ${individual.individualId}`}
                      textEditorSubmitUrl={`/api/individual/${individual.individualGuid}/update/caseReviewDiscussion`}
                    />
                  }
                </div>
                : null
            }
            {
              showDetails ?
                <div style={{ padding: '0px 0px 10px 0px' }}>
                  {
                    <TextFieldView
                      isEditable={user.is_staff || user.canEdit}
                      fieldName="Individual Notes"
                      initialText={individual.notes}
                      textEditorId={EDIT_INDIVIDUAL_INFO_MODAL_ID}
                      textEditorTitle={`Notes for Individual ${individual.individualId}`}
                      textEditorSubmitUrl={`/api/individual/${individual.individualGuid}/update/notes`}
                    />
                  }
                </div>
                : null
            }
            <PhenotipsDataPanel
              project={project}
              individual={individual}
              showDetails={showDetails}
              showEditPhenotipsLink={user.hasEditPermissions}
            />
          </Grid.Column>
          <Grid.Column width={3}>
            <div>
              {
                individual.sampleGuids.map((sampleGuid) => {
                  const sample = this.props.samplesByGuid[sampleGuid]
                  let loadedVariantCallDatasets = sample.datasetGuids
                    .filter(datasetGuid => (
                      this.props.datasetsByGuid[datasetGuid].analysisType === ANALYSIS_TYPE_VARIANT_CALLS &&
                      this.props.datasetsByGuid[datasetGuid].isLoaded
                    ))
                    .map(datasetGuid => this.props.datasetsByGuid[datasetGuid])

                  loadedVariantCallDatasets = orderBy(loadedVariantCallDatasets, [d => d.loadedDate], 'desc')

                  return (
                    <div key={sampleGuid}>
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
              }
            </div>
          </Grid.Column>
        </Grid.Row>
      </Grid>)
  }
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
  showDetails: getShowDetails(state),
  samplesByGuid: getSamplesByGuid(state),
  datasetsByGuid: getDatasetsByGuid(state),
})

export default connect(mapStateToProps)(IndividualRow)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import orderBy from 'lodash/orderBy'

import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import PhenotipsDataPanel from 'shared/components/panel/view-phenotips-info/PhenotipsDataPanel'
import Sample from 'shared/components/panel/sample'
import { FamilyLayout } from 'shared/components/panel/family'
import { ColoredIcon } from 'shared/components/StyledComponents'

import { updateIndividual } from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import { getProject, getProjectSamplesByGuid } from 'pages/Project/selectors'
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

class IndividualRow extends React.Component
{
  static propTypes = {
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    samplesByGuid: PropTypes.object.isRequired,
    updateIndividual: PropTypes.func,
    editCaseReview: PropTypes.bool,
  }

  render() {
    const { user, project, family, individual, editCaseReview } = this.props

    const { individualId, displayName, paternalId, maternalId, sex, affected, createdDate } = individual

    let loadedSamples = individual.sampleGuids.map(
      sampleGuid => this.props.samplesByGuid[sampleGuid],
    ).filter(s =>
      s.datasetType === DATASET_TYPE_VARIANT_CALLS &&
      s.sampleStatus === SAMPLE_STATUS_LOADED,
    )
    loadedSamples = orderBy(loadedSamples, [s => s.loadedDate], 'desc')
    // only show first and latest samples
    loadedSamples.splice(1, loadedSamples.length - 2)

    const sampleDetails = loadedSamples.map((sample, i) =>
      <div key={sample.sampleGuid}>
        <Sample loadedSample={sample} isOutdated={i !== 0} />
      </div>,
    )

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
      </CaseReviewDropdownContainer> : sampleDetails

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
              individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED
              || (editCaseReview && individual.caseReviewDiscussion) || false
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
  user: getUser(state),
  project: getProject(state),
  samplesByGuid: getProjectSamplesByGuid(state),
})

const mapDispatchToProps = {
  updateIndividual,
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

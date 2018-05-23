/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import EditTextButton from 'shared/components/buttons/EditTextButton'
import { updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
} from 'shared/constants/caseReviewConstants'

const StatusContainer = styled.span`
  display: inline-block;
  whitespace: nowrap;
  min-width: 220px;
`

const STATUS_FORM_FIELDS = [{
  name: 'caseReviewStatus',
  component: 'select',
  tabIndex: '1',
  style: { margin: '3px !important', maxWidth: '170px', display: 'inline-block', padding: '0px !important', marginRight: '10px' },
  children: CASE_REVIEW_STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.name}</option>),
}]

const CaseReviewStatusForm = (props) => {
  const initialValues = { caseReviewStatus: props.individual.caseReviewStatus }
  return (
    <ReduxFormWrapper
      onSubmit={props.updateIndividual}
      form={`editCaseReviewStatus-${props.individual.individualGuid}`}
      initialValues={initialValues}
      closeOnSuccess={false}
      submitOnChange
      fields={STATUS_FORM_FIELDS}
    />
  )
}

CaseReviewStatusForm.propTypes = {
  individual: PropTypes.object.isRequired,
  updateIndividual: PropTypes.func.isRequired,
}

const CaseReviewStatusDropdown = props =>
  <StatusContainer>
    <CaseReviewStatusForm {...props} />
    {/* edit case review discussion for individual: */}
    <div>
      {
        props.individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED &&
        <EditTextButton
          label="Edit Questions"
          initialText={props.individual.caseReviewDiscussion}
          fieldId="caseReviewDiscussion"
          modalTitle={`${props.individual.individualId}: Case Review Discussion`}
          modalId={`editCaseReviewDiscussion -${props.individual.individualGuid}`}
          onSubmit={props.updateIndividual}
        />
      }
    </div>
  </StatusContainer>

export { CaseReviewStatusDropdown as CaseReviewStatusDropdownComponent }

CaseReviewStatusDropdown.propTypes = {
  individual: PropTypes.object.isRequired,
  updateIndividual: PropTypes.func.isRequired,
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateIndividual: (values) => {
      dispatch(updateIndividual(ownProps.individual.individualGuid, values))
    },
  }
}

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

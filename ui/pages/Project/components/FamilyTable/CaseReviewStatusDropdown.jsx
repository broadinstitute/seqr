/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Checkbox } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import EditTextButton from 'shared/components/buttons/EditTextButton'
import { VerticalSpacer } from 'shared/components/Spacers'
import { updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_ACCEPTED,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS,
} from 'shared/constants/caseReviewConstants'

const StatusContainer = styled.span`
  display: inline-block;
  whitespace: nowrap;
  min-width: 220px;
`

const AcceptedForCheckbox = styled(Checkbox)`
  padding: 3px 10px 5px 5px;
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

const CaseReviewAcceptedForForm = (props) => {
  const initialValues = { caseReviewStatusAcceptedFor: props.individual.caseReviewStatusAcceptedFor }
  const fields = CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS.map((option, k) => {
    if (option === '---') {
      return { component: 'br', name: k, displayOnly: true }
    }

    return ({
      key: option.value,
      name: 'caseReviewStatusAcceptedFor',
      component: ({ value, onChange }) => //eslint-disable-line react/prop-types
        <AcceptedForCheckbox
          defaultChecked={props.individual.caseReviewStatusAcceptedFor !== null && props.individual.caseReviewStatusAcceptedFor.includes(option.value)}
          label={option.name}
          value={option.value}
          onChange={(e, result) => {
            if (result.checked) {
              value += result.value
            } else {
              value = value.replace(result.value, '')
            }
            onChange(value)
          }}
        />,
    })
  })
  return (
    <ReduxFormWrapper
      onSubmit={props.updateIndividual}
      form={`editCaseReviewStatusAcceptedFor-${props.individual.individualGuid}`}
      initialValues={initialValues}
      closeOnSuccess={false}
      submitOnChange
      fields={fields}
    />
  )
}

CaseReviewAcceptedForForm.propTypes = {
  individual: PropTypes.object.isRequired,
  updateIndividual: PropTypes.func.isRequired,
}

const CaseReviewStatusDropdown = props =>
  <StatusContainer>
    <CaseReviewStatusForm {...props} />
    {
      props.individual.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED &&
        <div>
          <VerticalSpacer height={5} />
          <CaseReviewAcceptedForForm {...props} />
        </div>
    }
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

/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Field } from 'redux-form'
import { Checkbox } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import EditTextButton from 'shared/components/buttons/EditTextButton'
import { updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_ACCEPTED,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS,
} from 'shared/constants/caseReviewConstants'


const CaseReviewStatusDropdown = props =>
  <div style={{ display: 'inline-block', whitespace: 'nowrap', minWidth: '220px' }}>
    <ReduxFormWrapper
      onSubmit={props.updateIndividual}
      form={`editCaseReview-${props.individual.individualGuid}`}
      initialValues={props.individual}
      closeOnSuccess={false}
      submitOnChange
    >
      <Field
        name="caseReviewStatus"
        component="select"
        tabIndex="1"
        style={{ margin: '3px !important', maxWidth: '170px', display: 'inline-block', padding: '0px !important' }}
      >
        {
          CASE_REVIEW_STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.name}</option>)
        }
      </Field>
      {
        props.individual.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED ?
          CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS.map((option, k) => {
              if (option === '---') {
                return <br key={k} />
              }

              return (
                <Field
                  key={option.value}
                  name="caseReviewStatusAcceptedFor"
                  component={({ input }) =>
                    <Checkbox
                      defaultChecked={props.individual.caseReviewStatusAcceptedFor !== null && props.individual.caseReviewStatusAcceptedFor.includes(option.value)}
                      style={{ padding: '3px 10px 5px 5px' }}
                      label={option.name}
                      value={option.value}
                      onChange={(e, result) => {
                        if (result.checked) {
                          input.value += result.value
                        } else {
                          input.value = input.value.replace(result.value, '')
                        }
                        input.onChange(input.value)
                      }}
                    />
                  }
                />
              )
            }) : null
      }
    </ReduxFormWrapper>
    {/* edit case review discussion for individual: */}
    <div>
      {
        props.individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED &&
        <EditTextButton
          label="Edit Questions"
          initialValues={props.individual}
          fieldId="caseReviewDiscussion"
          modalTitle={`${props.individual.individualId}: Case Review Discussion`}
          modalId={`editCaseReviewDiscussion -${props.individual.individualGuid}`}
          onSubmit={props.updateIndividual}
        />
      }
    </div>
  </div>

export { CaseReviewStatusDropdown as CaseReviewStatusDropdownComponent }

CaseReviewStatusDropdown.propTypes = {
  individual: PropTypes.object.isRequired,
  updateIndividual: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  updateIndividual,
}

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

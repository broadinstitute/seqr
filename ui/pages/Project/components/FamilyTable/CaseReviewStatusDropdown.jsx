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
      form={`editCaseReviewStatus-${props.individual.individualGuid}`}
      initialValues={{ caseReviewStatus: props.individual.caseReviewStatus }}
      closeOnSuccess={false}
      submitOnChange
    >
      <Field
        name="caseReviewStatus"
        component="select"
        tabIndex="1"
        style={{ margin: '3px !important', maxWidth: '170px', display: 'inline-block', padding: '0px !important', marginRight: '10px' }}
      >
        {
          CASE_REVIEW_STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.name}</option>)
        }
      </Field>
    </ReduxFormWrapper>
    {
      props.individual.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED ?
        <div style={{ padding: '5px 0px 10px 0px' }}>
          <ReduxFormWrapper
            onSubmit={props.updateIndividual}
            form={`editCaseReviewStatusAcceptedFor-${props.individual.individualGuid}`}
            initialValues={{ caseReviewStatusAcceptedFor: props.individual.caseReviewStatusAcceptedFor }}
            closeOnSuccess={false}
            submitOnChange
          >
            {CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS.map((option, k) => {
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
            })}
          </ReduxFormWrapper>
        </div>
        : null
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
  </div>

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

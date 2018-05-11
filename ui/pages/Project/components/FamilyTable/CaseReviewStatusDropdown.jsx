/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Checkbox } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_ACCEPTED,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS,
} from '../../constants'


const CaseReviewStatusDropdown = props =>
  <div style={{ display: 'inline-block', whitespace: 'nowrap', minWidth: '220px' }}>
    <ReduxFormWrapper
      onSubmit={props.updateIndividual}
      form={`editCaseReview-${props.individual.individualGuid}`}
      initialValues={props.individual}
      closeOnSuccess={false}
      submitOnChange
      fields={[{
        name: 'caseReviewStatus',
        component: 'select',
        tabIndex: '1',
        style: { margin: '3px !important', maxWidth: '170px', display: 'inline-block', padding: '0px !important', marginRight: '10px' },
        children: CASE_REVIEW_STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.name}</option>),
      }]}
    />
    {
      props.individual.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED &&
        <div style={{ padding: '5px 0px 10px 0px' }}>
          <ReduxFormWrapper
            onSubmit={props.updateIndividual}
            form={`editCaseReviewStatusAcceptedFor-${props.individual.individualGuid}`}
            initialValues={props.individual}
            closeOnSuccess={false}
            submitOnChange
            fields={CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS.map((option, k) => {
              if (option === '---') {
                return { component: 'br', name: k, displayOnly: true }
              }

              return ({
                key: option.value,
                name: 'caseReviewStatusAcceptedFor',
                component: ({ value, onChange }) => //eslint-disable-line react/prop-types
                  <Checkbox
                    defaultChecked={props.individual.caseReviewStatusAcceptedFor !== null && props.individual.caseReviewStatusAcceptedFor.includes(option.value)}
                    style={{ padding: '3px 10px 5px 5px' }}
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
            })}
          />
        </div>
    }
    {/* edit case review discussion for individual: */}
    <div>
      {
        props.individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED &&
        <TextFieldView
          hideValue
          isEditable
          editLabel="Edit Questions"
          initialValues={props.individual}
          field="caseReviewDiscussion"
          idField="individualGuid"
          modalTitle={`${props.individual.individualId}: Case Review Discussion`}
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

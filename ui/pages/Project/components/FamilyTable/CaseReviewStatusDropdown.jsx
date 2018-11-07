/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { Select } from 'shared/components/form/Inputs'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
} from '../../constants'

const StatusContainer = styled.span`
  display: inline-block;
  whitespace: nowrap;
  min-width: 220px;
  
  .ui.selection.active.dropdown .menu {
    max-height: none;
  }
`

const STATUS_FORM_FIELDS = [{
  name: 'caseReviewStatus',
  component: Select,
  tabIndex: '1',
  options: CASE_REVIEW_STATUS_OPTIONS,
}]

const CaseReviewStatusDropdown = props =>
  <StatusContainer>
    <ReduxFormWrapper
      onSubmit={props.updateIndividual}
      form={`editCaseReviewStatus-${props.individual.individualGuid}`}
      initialValues={props.individual}
      closeOnSuccess={false}
      submitOnChange
      fields={STATUS_FORM_FIELDS}
    />
    {/* edit case review discussion for individual: */}
    <div style={{ padding: '5px 12px' }}>
      {
        props.individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED &&
        <TextFieldView
          hideValue
          isEditable
          editLabel="Edit Questions"
          initialValues={props.individual}
          field="caseReviewDiscussion"
          idField="individualGuid"
          modalTitle={`${props.individual.displayName}: Case Review Discussion`}
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
    updateIndividual: (updates) => {
      dispatch(updateIndividual({ individualGuid: ownProps.individual.individualGuid, ...updates }))
    },
  }
}

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

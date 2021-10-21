import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import StateChangeForm from 'shared/components/form/StateChangeForm'
import { Select } from 'shared/components/form/Inputs'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { camelcaseToTitlecase, toSnakecase } from 'shared/utils/stringUtils'
import { updateIndividual } from 'redux/rootReducer'

import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
} from '../../constants'

const StatusContainer = styled.span`
  display: inline-block;
  whitespace: nowrap;
  min-width: 220px;
  
  .ui.form {
    width: 100%;
  }
  
  .ui.selection.active.dropdown .menu {
    max-height: none;
  }
  
  button.ui.button.basic.tiny.labeled.icon {
    padding-top: 8px;
  }
`

const STATUS_FORM_FIELDS = [{
  name: 'caseReviewStatus',
  component: Select,
  tabIndex: '1',
  options: CASE_REVIEW_STATUS_OPTIONS,
}]

const CaseReviewStatusDropdown = React.memo(props => (
  <StatusContainer>
    <StateChangeForm
      updateField={props.updateIndividualField}
      initialValues={props.individual}
      fields={STATUS_FORM_FIELDS}
    />
    {props.individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED && (
      <TextFieldView
        hideValue
        isEditable
        editLabel="Edit Questions"
        initialValues={props.individual}
        field="caseReviewDiscussion"
        idField="individualGuid"
        modalTitle={`${props.individual.displayName}: Case Review Discussion`}
        onSubmit={props.updateIndividualDiscussion}
      />
    )}
  </StatusContainer>
))

export { CaseReviewStatusDropdown as CaseReviewStatusDropdownComponent }

CaseReviewStatusDropdown.propTypes = {
  individual: PropTypes.object.isRequired,
  updateIndividualField: PropTypes.func.isRequired,
  updateIndividualDiscussion: PropTypes.func.isRequired,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  updateIndividualField: individualField => (value) => {
    dispatch(updateIndividual({
      individualGuid: ownProps.individual.individualGuid,
      individualField: toSnakecase(camelcaseToTitlecase(individualField)),
      [individualField]: value,
    }))
  },
  updateIndividualDiscussion: (updates) => {
    dispatch(updateIndividual(
      { individualGuid: ownProps.individual.individualGuid, individualField: 'case_review_discussion', ...updates },
    ))
  },
})

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

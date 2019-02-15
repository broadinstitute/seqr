/* eslint-disable jsx-a11y/label-has-for */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import EditRecordsForm from 'shared/components/form/EditRecordsForm'
import { FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID } from 'shared/utils/constants'
import { INDIVIDUAL_FIELDS } from '../../constants'
import { updateIndividuals } from '../../reducers'
import { getProjectAnalysisGroupIndividualsByGuid } from '../../selectors'


const EditIndividualsForm = props =>
  <EditRecordsForm
    formName="editIndividuals"
    idField="individualGuid"
    entityKey="individuals"
    defaultSortColumn={FAMILY_FIELD_ID}
    filterColumn={INDIVIDUAL_FIELD_ID}
    columns={INDIVIDUAL_FIELDS}
    {...props}
  />

EditIndividualsForm.propTypes = {
  records: PropTypes.object.isRequired,
  onSubmit: PropTypes.func.isRequired,
  modalName: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  records: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
})

const mapDispatchToProps = {
  onSubmit: updateIndividuals,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditIndividualsForm)

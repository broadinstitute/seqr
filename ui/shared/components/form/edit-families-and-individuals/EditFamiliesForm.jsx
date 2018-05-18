import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import EditRecordsForm from 'shared/components/form/EditRecordsForm'
import { updateFamilies } from 'pages/Project/reducers'
import { getProjectFamilies } from 'pages/Project/selectors'

const FAMILY_FIELDS = [
  {
    header: 'Family Id',
    field: 'familyId',
    fieldProps: { component: ({ input }) => input.value },
    cellProps: { collapsing: true, style: { minWidth: '100px' } },
  },
  {
    header: 'Family Description',
    field: 'description',
    fieldProps: { component: 'input', type: 'text' },
    cellProps: { style: { paddingRight: '150px' } },
  },
]

const EditFamiliesForm = props =>
  <EditRecordsForm
    formName="editFamilies"
    modalName={props.modalName}
    records={props.families}
    fields={FAMILY_FIELDS}
    onSubmit={({ records, ...values }) => props.updateFamilies({ families: records, ...values })}
  />

EditFamiliesForm.propTypes = {
  families: PropTypes.array.isRequired,
  updateFamilies: PropTypes.func.isRequired,
  modalName: PropTypes.string,
}

export { EditFamiliesForm as EditFamiliesFormComponent }

const mapStateToProps = state => ({
  families: getProjectFamilies(state),
})

const mapDispatchToProps = {
  updateFamilies,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditFamiliesForm)

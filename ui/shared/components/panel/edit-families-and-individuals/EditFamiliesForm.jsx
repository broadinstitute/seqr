import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import EditRecordsForm from 'shared/components/form/EditRecordsForm'
import { getProjectFamilies, updateFamilies } from 'redux/rootReducer'

const EditFamiliesForm = props =>
  <EditRecordsForm
    formName="editFamilies"
    records={props.families}
    fields={[
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
    ]}
    onSubmit={props.updateFamilies}
    onDelete={vals => console.log(vals)}
    onClose={props.onClose}
  />

EditFamiliesForm.propTypes = {
  families: PropTypes.array.isRequired,
  updateFamilies: PropTypes.func.isRequired,
  onClose: PropTypes.func,
}

export { EditFamiliesForm as EditFamiliesFormComponent }

const mapStateToProps = state => ({
  families: getProjectFamilies(state),
})

const mapDispatchToProps = {
  updateFamilies,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditFamiliesForm)

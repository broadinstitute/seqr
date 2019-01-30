import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import EditRecordsForm from 'shared/components/form/EditRecordsForm'
import { FAMILY_FIELD_ID } from 'shared/utils/constants'
import { FAMILY_FIELDS } from '../../constants'
import { updateFamilies } from '../../reducers'
import { getProjectFamiliesByGuid } from '../../selectors'


const EditFamiliesForm = props =>
  <EditRecordsForm
    formName="editFamilies"
    modalName={props.modalName}
    idField="familyGuid"
    entityKey="families"
    defaultSortColumn={FAMILY_FIELD_ID}
    filterColumn={FAMILY_FIELD_ID}
    columns={FAMILY_FIELDS}
    {...props}
  />

EditFamiliesForm.propTypes = {
  records: PropTypes.object.isRequired,
  onSubmit: PropTypes.func.isRequired,
  modalName: PropTypes.string,
}

const mapStateToProps = state => ({
  records: getProjectFamiliesByGuid(state),
})

const mapDispatchToProps = {
  onSubmit: updateFamilies,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditFamiliesForm)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import DataLoader from 'shared/components/DataLoader'
import EditRecordsForm from 'shared/components/form/EditRecordsForm'
import { FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID } from 'shared/utils/constants'
import { INDIVIDUAL_FIELDS } from '../../constants'
import { loadIndividuals, updateIndividuals } from '../../reducers'
import { getProjectAnalysisGroupIndividualsByGuid, getIndivdualsLoading } from '../../selectors'

const EditIndividualsForm = React.memo(({ load, loading, ...props }) => (
  <DataLoader load={load} content={props.records} loading={loading}>
    <EditRecordsForm
      idField="individualGuid"
      entityKey="individuals"
      defaultSortColumn={FAMILY_FIELD_ID}
      filterColumn={INDIVIDUAL_FIELD_ID}
      columns={INDIVIDUAL_FIELDS}
      {...props}
    />
  </DataLoader>
))

EditIndividualsForm.propTypes = {
  records: PropTypes.object.isRequired,
  onSubmit: PropTypes.func.isRequired,
  modalName: PropTypes.string,
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  loading: getIndivdualsLoading(state),
  records: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
})

const mapDispatchToProps = {
  load: loadIndividuals,
  onSubmit: updateIndividuals,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditIndividualsForm)

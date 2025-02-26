import React from 'react'
import PropTypes from 'prop-types'

import { validators } from 'shared/components/form/FormHelpers'
import SubmitFormPage from 'shared/components/page/SubmitFormPage'

const FIELDS = [
  {
    name: 'file',
    label: 'QC Pipeline Output File Path',
    placeholder: 'gs:// Google bucket path',
    validate: validators.required,
  },
]

const TriggerDagForm = ({ dagName }) => (
  <SubmitFormPage
    header={`Trigger ${dagName} DAG`}
    url={`/api/data_management/trigger_dag/${dagName}`}
    fields={FIELDS}
  />
)

TriggerDagForm.propTypes = {
  dagName: PropTypes.string,
}

const TriggerDeleteProjectsDag = () => (
  <TriggerDagForm dagName="DELETE_PROJECTS" />
)

const TriggerDeleteFamiliesDag = () => (
  <TriggerDagForm dagName="DELETE_FAMILIES" />
)

const TriggerUpdateReferenceDatasetDag = () => (
  <TriggerDagForm dagName="UPDATE_REFERENCE_DATASETS" />
)

export default [
  { path: 'delete_search_projects', component: TriggerDeleteProjectsDag },
  { path: 'delete_search_families', component: TriggerDeleteFamiliesDag },
  { path: 'update_search_reference_data', component: TriggerUpdateReferenceDatasetDag },
]

import React from 'react'
import PropTypes from 'prop-types'

import { validators } from 'shared/components/form/FormHelpers'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import SubmitFormPage from 'shared/components/page/SubmitFormPage'

const FIELDS = [
  {
    name: 'project',
    label: 'Project',
    control: AwesomeBarFormInput,
    categories: ['projects'],
    fluid: true,
    placeholder: 'Search for a project',
    validate: validators.required,
  },
  // TODO optional dataset type
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

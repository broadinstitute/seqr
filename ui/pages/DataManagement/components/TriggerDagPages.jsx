import React from 'react'
import PropTypes from 'prop-types'

import { validators } from 'shared/components/form/FormHelpers'
import { Select } from 'shared/components/form/Inputs'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import SubmitFormPage from 'shared/components/page/SubmitFormPage'
import {
  DATASET_TYPE_SNV_INDEL_CALLS,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
  GENOME_VERSION_FIELD,
} from 'shared/utils/constants'

const DATASET_TYPE_FIELD = {
  name: 'datasetType',
  label: 'Dataset Type',
  component: Select,
  options: [
    DATASET_TYPE_SNV_INDEL_CALLS, DATASET_TYPE_MITO_CALLS, DATASET_TYPE_SV_CALLS,
  ].map(value => ({ value, name: value })),
  validate: validators.required,
}
const PROJECT_FIELDS = [
  {
    name: 'project',
    label: 'Project',
    control: AwesomeBarFormInput,
    categories: ['projects'],
    fluid: true,
    placeholder: 'Search for a project',
    validate: validators.required,
  },
  DATASET_TYPE_FIELD,
]
const FAMILY_FIELDS = [
  {
    name: 'family',
    label: 'Family',
    control: AwesomeBarFormInput,
    categories: ['families'],
    fluid: true,
    placeholder: 'Search for a family',
    validate: validators.required,
  },
  DATASET_TYPE_FIELD,
]
const REFERENCE_DATASET_FIELDS = [
  { ...GENOME_VERSION_FIELD, validate: validators.required },
  DATASET_TYPE_FIELD,
]

const TriggerDagForm = ({ dagName, fields }) => (
  <SubmitFormPage
    header={`Trigger ${dagName} DAG`}
    url={`/api/data_management/trigger_dag/${dagName}`}
    fields={fields}
  />
)

TriggerDagForm.propTypes = {
  dagName: PropTypes.string,
  fields: PropTypes.arrayOf(PropTypes.object),
}

const TriggerDeleteProjectsDag = () => (
  <TriggerDagForm dagName="DELETE_PROJECTS" fields={PROJECT_FIELDS} />
)

const TriggerDeleteFamiliesDag = () => (
  <TriggerDagForm dagName="DELETE_FAMILIES" fields={FAMILY_FIELDS} />
)

const TriggerUpdateReferenceDatasetDag = () => (
  <TriggerDagForm dagName="UPDATE_REFERENCE_DATASETS" fields={REFERENCE_DATASET_FIELDS} />
)

export default [
  { path: 'delete_search_projects', component: TriggerDeleteProjectsDag },
  { path: 'delete_search_families', component: TriggerDeleteFamiliesDag },
  { path: 'update_search_reference_data', component: TriggerUpdateReferenceDatasetDag },
]

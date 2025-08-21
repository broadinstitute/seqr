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
} from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

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

const TriggerSearchDataUpdateForm = ({ path, fields }) => (
  <SubmitFormPage
    header={`Trigger ${snakecaseToTitlecase(path)}`}
    url={`/api/data_management/trigger_${path}`}
    fields={fields}
  />
)

TriggerSearchDataUpdateForm.propTypes = {
  path: PropTypes.string,
  fields: PropTypes.arrayOf(PropTypes.object),
}

const TriggerDeleteProjects = () => (
  <TriggerSearchDataUpdateForm path="delete_project" fields={PROJECT_FIELDS} />
)

const TriggerDeleteFamilies = () => (
  <TriggerSearchDataUpdateForm path="delete_family" fields={FAMILY_FIELDS} />
)

export default [
  { path: 'delete_search_project', component: TriggerDeleteProjects },
  { path: 'delete_search_family', component: TriggerDeleteFamilies },
]

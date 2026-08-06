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
  { ...DATASET_TYPE_FIELD, name: 'datasetTypes', multiple: true },
]

const TriggerSearchDataUpdateForm = ({ entity, fields }) => (
  <SubmitFormPage
    header={`Trigger Delete ${snakecaseToTitlecase(entity)} Search`}
    url={`/api/data_management/trigger_delete_${entity}`}
    fields={fields}
  />
)

TriggerSearchDataUpdateForm.propTypes = {
  entity: PropTypes.string,
  fields: PropTypes.arrayOf(PropTypes.object),
}

const TriggerDeleteProjects = () => (
  <TriggerSearchDataUpdateForm entity="project" fields={PROJECT_FIELDS} />
)

const TriggerDeleteFamilies = () => (
  <TriggerSearchDataUpdateForm entity="family" fields={FAMILY_FIELDS} />
)

export default [
  { path: 'delete_search_project', component: TriggerDeleteProjects },
  { path: 'delete_search_family', component: TriggerDeleteFamilies },
]

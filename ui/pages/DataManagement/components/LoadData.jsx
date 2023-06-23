import React from 'react'
import { FormSpy } from 'react-final-form'

import { validators } from 'shared/components/form/FormHelpers'
import FormWizard from 'shared/components/form/FormWizard'
import { ButtonRadioGroup } from 'shared/components/form/Inputs'
import LoadOptionsSelect from 'shared/components/form/LoadOptionsSelect'
import { SAMPLE_TYPE_EXOME, SAMPLE_TYPE_GENOME, DATASET_TYPE_SV_CALLS, DATASET_TYPE_MITO_CALLS } from 'shared/utils/constants'

const formatProjectOption = ({ name, projectGuid, dataTypeLastLoaded }) => ({
  value: projectGuid,
  text: name,
  description: dataTypeLastLoaded && `Last Loaded: ${new Date(dataTypeLastLoaded).toLocaleDateString()}`,
  color: dataTypeLastLoaded ? 'teal' : 'orange',
})

const renderLabel = ({ color, text }) => ({ color, content: text })

const SUBSCRIPTION = { values: true }
const LoadedProjectOptions = props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <LoadOptionsSelect
        url={`/api/data_management/loaded_projects/${values.sampleType}/${values.datasetType}`}
        formatOption={formatProjectOption}
        optionsResponseKey="projects"
        validationErrorMessage="No Projects Found"
        multiple
        search
        renderLabel={renderLabel}
        {...props}
      />
    )}
  </FormSpy>
)

const LOAD_DATA_PAGES = [
  {
    fields: [
      {
        name: 'filePath',
        label: 'Callset File Path',
        placeholder: 'gs://',
        validate: validators.required,
      },
      {
        name: 'sampleType',
        label: 'Sample Type',
        component: ButtonRadioGroup,
        options: [SAMPLE_TYPE_EXOME, SAMPLE_TYPE_GENOME].map(value => ({ value, text: value })),
        validate: validators.required,
      },
      {
        name: 'datasetType',
        label: 'Dataset Type',
        component: ButtonRadioGroup,
        options: [DATASET_TYPE_SV_CALLS, DATASET_TYPE_MITO_CALLS].map(value => ({ value, text: value })),
        validate: validators.required,
      },
    ],
    submitUrl: '/api/data_management/validate_callset',
  },
  {
    fields: [
      {
        name: 'projects',
        label: 'Projects To Load',
        component: LoadedProjectOptions,
        validate: validators.required,
      },
    ],
  },
]

const formatSubmitUrl = () => '/api/data_management/load_data'

const LoadData = () => (
  <FormWizard
    pages={LOAD_DATA_PAGES}
    formatSubmitUrl={formatSubmitUrl}
    successMessage="Data loading has been triggered, and further updates will be posted in slack"
    noModal
  />
)

export default LoadData

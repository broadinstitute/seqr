import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'

import { getUser } from 'redux/selectors'
import { validators } from 'shared/components/form/FormHelpers'
import FormWizard from 'shared/components/form/FormWizard'
import { ButtonRadioGroup, InlineToggle } from 'shared/components/form/Inputs'
import LoadOptionsSelect from 'shared/components/form/LoadOptionsSelect'
import {
  SAMPLE_TYPE_EXOME,
  SAMPLE_TYPE_GENOME,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
  DATASET_TYPE_SNV_INDEL_CALLS,
  GENOME_VERSION_FIELD,
  LoadDataVCFMessage,
} from 'shared/utils/constants'

const formatProjectOption = opt => ({
  value: JSON.stringify(opt),
  text: opt.name,
  description: [
    opt.sampleIds && `${opt.sampleIds.length} Samples to Load`,
    opt.dataTypeLastLoaded && `Last Loaded: ${new Date(opt.dataTypeLastLoaded).toLocaleDateString()}`,
  ].filter(val => val).join('; '),
  color: opt.dataTypeLastLoaded ? 'teal' : 'orange',
})

const renderLabel = ({ color, text }) => ({ color, content: text })

const SUBSCRIPTION = { values: true }
const LoadedProjectOptions = props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <LoadOptionsSelect
        url={`/api/data_management/loaded_projects/${values.genomeVersion}/${values.sampleType}/${values.datasetType || DATASET_TYPE_SNV_INDEL_CALLS}`}
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

const FILE_PATH_FIELD = {
  name: 'filePath',
  validate: validators.required,
}

const CALLSET_PAGE_FIELDS = [
  {
    name: 'skipValidation',
    label: 'Skip Callset Validation',
    component: InlineToggle,
    asFormInput: true,
  },
  {
    ...GENOME_VERSION_FIELD,
    component: ButtonRadioGroup,
    validate: validators.required,
  },
  {
    name: 'sampleType',
    label: 'Sample Type',
    component: ButtonRadioGroup,
    options: [SAMPLE_TYPE_EXOME, SAMPLE_TYPE_GENOME].map(value => ({ value, text: value })),
    validate: validators.required,
  },
]

const CALLSET_PAGE = {
  fields: [
    {
      label: 'VCF',
      component: LoadOptionsSelect,
      url: '/api/data_management/loading_vcfs',
      optionsResponseKey: 'vcfs',
      validationErrorMessage: 'No VCFs found in the loading datasets directory',
      ...FILE_PATH_FIELD,
    },
    ...CALLSET_PAGE_FIELDS,
  ],
  submitUrl: '/api/data_management/validate_callset',
}

const MULTI_DATA_TYPE_CALLSET_PAGE = {
  ...CALLSET_PAGE,
  fields: [
    {
      label: 'Callset File Path',
      placeholder: 'gs://',
      ...FILE_PATH_FIELD,
    },
    {
      name: 'skipSRChecks',
      label: 'Skip Sex and Relatedness Checks',
      component: InlineToggle,
      asFormInput: true,
    },
    ...CALLSET_PAGE_FIELDS,
    {
      name: 'datasetType',
      label: 'Dataset Type',
      component: ButtonRadioGroup,
      options: [
        DATASET_TYPE_SNV_INDEL_CALLS,
        DATASET_TYPE_SV_CALLS,
        DATASET_TYPE_MITO_CALLS,
      ].map(value => ({ value, text: value.replace('_', '/') })),
      validate: validators.required,
    },
  ],
}

const ADDITIONAL_LOAD_DATA_PAGES = [
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

const LOAD_DATA_PAGES = [CALLSET_PAGE, ...ADDITIONAL_LOAD_DATA_PAGES]
const MULTI_DATA_TYPE_LOAD_DATA_PAGES = [MULTI_DATA_TYPE_CALLSET_PAGE, ...ADDITIONAL_LOAD_DATA_PAGES]

const formatSubmitUrl = () => '/api/data_management/load_data'

const LoadData = ({ user }) => (
  <div>
    {!user.isAnvil && <LoadDataVCFMessage isAnvil={false} />}
    <FormWizard
      pages={user.isAnvil ? MULTI_DATA_TYPE_LOAD_DATA_PAGES : LOAD_DATA_PAGES}
      formatSubmitUrl={formatSubmitUrl}
      successMessage="Data loading has been triggered"
      noModal
    />
  </div>
)

LoadData.propTypes = {
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(LoadData)

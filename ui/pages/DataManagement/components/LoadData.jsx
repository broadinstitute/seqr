import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'

import { getUser } from 'redux/selectors'
import { validators } from 'shared/components/form/FormHelpers'
import FormWizard from 'shared/components/form/FormWizard'
import { ButtonRadioGroup, CheckboxGroup, InlineToggle } from 'shared/components/form/Inputs'
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
    name: 'sampleType',
    label: 'Sample Type',
    component: ButtonRadioGroup,
    options: [SAMPLE_TYPE_EXOME, SAMPLE_TYPE_GENOME].map(value => ({ value, text: value })),
    validate: validators.required,
  },
  {
    ...GENOME_VERSION_FIELD,
    component: ButtonRadioGroup,
    validate: validators.required,
  },
  {
    name: 'validationsToSkip',
    label: 'Skip Validations',
    component: CheckboxGroup,
    options: [
      {
        value: 'validate_expected_contig_frequency',
        text: 'Chromosome Frequency',
        description: `By default, VCFs will be checked to ensure they have a reasonable number of variants in each 
          chromosome, and loading will fail if some chromosomes are missing data. If there is a known reason why some 
          chromosomes may be missing variants, such as with gene panel data, this validation may be safely skipped.`,
      },
      {
        value: 'validate_sample_type',
        text: 'Sample Type',
        description: `By default, VCFs will be checked for a representative sample of coding and non-coding SNPs which 
          will then be used to assess whether the selected Sample Type aligns with the provided data. If there is a 
          known reason why this validation would fail, such as WES data that uses broader capture regions, this 
          validation may be safely skipped.`,
      },
      {
        value: 'validate_no_duplicate_variants',
        text: 'Duplicate Variants (modifies data before loading)',
        description: `By default, VCFs will be checked to ensure they have no duplicate variants, as all supported  
          calling pipelines should have a single row per variant. While there are no well supported reasons why a VCF 
          with duplicate data should be loaded to seqr, we do provide this option to skip that validation and instead 
          deduplicate the data before running. NOTE: By selecting this option, variants will be ARBITRARILY DEDUPLICATED. 
          This means duplicate rows will be dropped at random to leave only one row per variant. If you want a more 
          deterministic approach to merging/ deduplicating your data, this should be done outside of seqr.`,
      },
    ],
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
    ...CALLSET_PAGE_FIELDS,
    {
      name: 'skipSRChecks',
      label: 'Skip Sex and Relatedness Checks',
      component: InlineToggle,
      asFormInput: true,
    },
    {
      name: 'skipTDR',
      label: 'Skip TDR Metrics',
      component: InlineToggle,
      asFormInput: true,
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

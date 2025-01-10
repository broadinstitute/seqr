import React from 'react'
import { Icon, Form, Label, Message } from 'semantic-ui-react'
import flatten from 'lodash/flatten'

import { validators } from '../components/form/FormHelpers'
import {
  BooleanCheckbox,
  RadioGroup,
  Dropdown,
  Select,
  InlineToggle,
  Pagination,
  BaseSemanticInput,
} from '../components/form/Inputs'

import { stripMarkdown, snakecaseToTitlecase, camelcaseToTitlecase } from './stringUtils'
import { ColoredIcon } from '../components/StyledComponents'
import HpoPanel from '../components/panel/HpoPanel'

export const ANVIL_URL = 'https://anvil.terra.bio'
export const LOCAL_LOGIN_URL = '/login'

export const VCF_DOCUMENTATION_URL = 'https://storage.googleapis.com/seqr-reference-data/seqr-vcf-info.pdf'

export const LoadDataVCFMessage = isAnvil => (
  <Message info compact>
    In order to load your data to seqr, you must
    {isAnvil ? ' have a joint called VCF available in your workspace. ' : ' use a joint called VCF.'}
    For more information about generating and validating this file,
    see &nbsp;
    <b><a href={VCF_DOCUMENTATION_URL} target="_blank" rel="noreferrer">this documentation</a></b>
  </Message>
)

export const GENOME_VERSION_37 = '37'
export const GENOME_VERSION_38 = '38'
export const GENOME_VERSION_OPTIONS = [
  { value: GENOME_VERSION_37, text: 'GRCh37' },
  { value: GENOME_VERSION_38, text: 'GRCh38' },
]
export const GENOME_VERSION_LOOKUP = GENOME_VERSION_OPTIONS.reduce(
  (acc, { value, text }) => ({ ...acc, [value]: text }), {},
)
export const GENOME_VERSION_FIELD = {
  name: 'genomeVersion', label: 'Genome Version', component: RadioGroup, options: GENOME_VERSION_OPTIONS,
}

export const GENOME_VERSION_DISPLAY_LOOKUP = {
  GRCh37: 'hg19',
  [GENOME_VERSION_37]: 'hg19',
  GRCh38: 'hg38',
  [GENOME_VERSION_38]: 'hg38',
}

// PROJECT FIELDS

export const FILE_FIELD_NAME = 'uploadedFile'

export const PROJECT_DESC_FIELD = { name: 'description', label: 'Project Description', placeholder: 'Description' }

export const CONSENT_CODES = ['HMB', 'GRU']
const CONSENT_CODE_OPTIONS = [...CONSENT_CODES, 'Other'].map(text => ({ text, value: text[0] }))
export const CONSENT_CODE_LOOKUP = CONSENT_CODE_OPTIONS.reduce(
  (acc, { value, text }) => ({ ...acc, [value]: text }), {},
)
const CONSENT_CODE_FIELD = {
  name: 'consentCode',
  label: 'Consent Code',
  component: RadioGroup,
  options: CONSENT_CODE_OPTIONS,
}

export const EDITABLE_PROJECT_FIELDS = [
  { name: 'name', label: 'Project Name', placeholder: 'Name', validate: validators.required, autoFocus: true },
  PROJECT_DESC_FIELD,
]

export const PM_EDITABLE_PROJECT_FIELDS = [
  ...EDITABLE_PROJECT_FIELDS,
  CONSENT_CODE_FIELD,
]

export const ANVIL_FIELDS = [
  {
    name: 'workspaceNamespace',
    label: 'Workspace Namespace',
    placeholder: 'AnVIL workspace name before the /',
    validate: validators.required,
    width: 8,
    inline: true,
  },
  {
    name: 'workspaceName',
    label: 'Workspace Name',
    placeholder: 'AnVIL workspace name after the /',
    validate: validators.required,
    width: 8,
    inline: true,
  },
]

export const FILE_FORMATS = [
  { title: 'Excel', ext: 'xls' },
  {
    title: 'Text',
    ext: 'tsv',
    formatLinks: [
      { href: 'https://en.wikipedia.org/wiki/Tab-separated_values', linkExt: 'tsv' },
      { href: 'https://en.wikipedia.org/wiki/Comma-separated_values', linkExt: 'csv' },
    ],
  },
]

const MAILTO_CONTACT_URL_REGEX = /^mailto:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}(,\s*[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{1,4})*$/i
export const MATCHMAKER_CONTACT_NAME_FIELD = { label: 'Contact Name' }
export const MATCHMAKER_CONTACT_URL_FIELD = {
  label: 'Contact URL',
  parse: val => `mailto:${val}`,
  format: val => (val || '').replace('mailto:', ''),
  validate: val => (MAILTO_CONTACT_URL_REGEX.test(val) ? undefined : 'Invalid contact url'),
}

// SAMPLES

export const DATASET_TYPE_SNV_INDEL_CALLS = 'SNV_INDEL'
export const DATASET_TYPE_SV_CALLS = 'SV'
export const DATASET_TYPE_MITO_CALLS = 'MITO'

export const DATA_TYPE_TPM = 'T'
export const DATA_TYPE_EXPRESSION_OUTLIER = 'E'
export const DATA_TYPE_SPLICE_OUTLIER = 'S'

export const DATASET_TITLE_LOOKUP = {
  [DATASET_TYPE_SV_CALLS]: ' SV',
  [DATASET_TYPE_MITO_CALLS]: ' Mitochondria',
  ONT_SNV_INDEL: ' ONT',
  [DATA_TYPE_TPM]: ' TPM',
  [DATA_TYPE_EXPRESSION_OUTLIER]: ' Expression Outlier',
  [DATA_TYPE_SPLICE_OUTLIER]: ' Splice Outlier',
}

export const SAMPLE_TYPE_EXOME = 'WES'
export const SAMPLE_TYPE_GENOME = 'WGS'

export const SAMPLE_TYPE_OPTIONS = [
  { value: SAMPLE_TYPE_EXOME, text: 'Exome' },
  { value: SAMPLE_TYPE_GENOME, text: 'Genome' },
]

// ANALYSIS STATUS

const FAMILY_STATUS_SOLVED = 'S'
const FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE = 'S_kgfp'
const FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'S_kgdp'
const FAMILY_STATUS_SOLVED_NOVEL_GENE = 'S_ng'
const FAMILY_STATUS_EXTERNAL_SOLVE = 'ES'
const FAMILY_STATUS_PROBABLE_SOLVE = 'PB'
const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE = 'Sc_kgfp'
const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'Sc_kgdp'
const FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE = 'Sc_ng'
const FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES = 'Rcpc'
const FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE = 'Rncc'
const FAMILY_STATUS_CLOSED = 'C'
const FAMILY_STATUS_PARTIAL_SOLVE = 'P'
const FAMILY_STATUS_ANALYSIS_IN_PROGRESS = 'I'
const FAMILY_STATUS_WAITING_FOR_DATA = 'Q'
const FAMILY_STATUS_LOADING_FAILED = 'F'
const FAMILY_STATUS_NO_DATA = 'N'

const DEPRECATED_FAMILY_ANALYSIS_STATUS_OPTIONS = [
  { value: FAMILY_STATUS_SOLVED, color: '#4CAF50', name: 'Solved' },
]
export const SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS = [
  { value: FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE, color: '#4CAF50', name: 'Solved - known gene for phenotype' },
  { value: FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE, color: '#4CAF50', name: 'Solved - gene linked to different phenotype' },
  { value: FAMILY_STATUS_SOLVED_NOVEL_GENE, color: '#4CAF50', name: 'Solved - novel gene' },
  { value: FAMILY_STATUS_EXTERNAL_SOLVE, color: '#146917', name: 'External Solve' },
  { value: FAMILY_STATUS_PROBABLE_SOLVE, color: '#ACD657', name: 'Probably Solved' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE, color: '#CDDC39', name: 'Strong candidate - known gene for phenotype' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE, color: '#CDDC39', name: 'Strong candidate - gene linked to different phenotype' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE, color: '#CDDC39', name: 'Strong candidate - novel gene' },
  { value: FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES, color: '#EB9F38', name: 'Reviewed, currently pursuing candidates' },
  { value: FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE, color: '#EF5350', name: 'Reviewed, no clear candidate' },
  { value: FAMILY_STATUS_CLOSED, color: '#9c0502', name: 'Closed, no longer under analysis' },
  { value: FAMILY_STATUS_PARTIAL_SOLVE, color: '#288582', name: 'Partial Solve - Analysis in Progress' },
  { value: FAMILY_STATUS_ANALYSIS_IN_PROGRESS, color: '#4682B4', name: 'Analysis in Progress' },
  { value: FAMILY_STATUS_WAITING_FOR_DATA, color: '#FFC107', name: 'Waiting for data' },
  { value: FAMILY_STATUS_LOADING_FAILED, color: '#ba4c12', name: 'Loading failed' },
  { value: FAMILY_STATUS_NO_DATA, color: '#646464', name: 'No data expected' },
]
export const ALL_FAMILY_ANALYSIS_STATUS_OPTIONS = [
  ...DEPRECATED_FAMILY_ANALYSIS_STATUS_OPTIONS, ...SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS,
]

export const FAMILY_ANALYSIS_STATUS_LOOKUP = ALL_FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
  (acc, tag) => ({ [tag.value]: tag, ...acc }), {},
)

export const SOLVED_FAMILY_STATUS_OPTIONS = new Set([
  FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE, FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_SOLVED_NOVEL_GENE, FAMILY_STATUS_EXTERNAL_SOLVE, FAMILY_STATUS_SOLVED,
])

export const SNP_DATA_TYPE = 'SNP'
export const FAMILY_ANALYSED_BY_DATA_TYPES = [
  [SNP_DATA_TYPE, 'WES/WGS'],
  ['SV', 'gCNV/SV'],
  ['RNA', 'RNAseq'],
  ['MT', 'Mitochondrial'],
  ['STR', 'STR'],
]

export const FAMILY_EXTERNAL_DATA_OPTIONS = [
  { value: 'M', color: '#3c9f6d', name: 'Methylation' },
  { value: 'P', color: '#1135cc', name: 'PacBio lrGS' },
  { value: 'R', color: '#5c2672', name: 'PacBio RNA' },
  { value: 'L', color: '#6583EC', name: 'ONT lrGS' },
  { value: 'O', color: '#644e96', name: 'ONT RNA' },
  { value: 'B', color: '#d0672d', name: 'BioNano' },
]

export const FAMILY_EXTERNAL_DATA_LOOKUP = FAMILY_EXTERNAL_DATA_OPTIONS.reduce(
  (acc, tag) => ({ [tag.value]: tag, ...acc }), {},
)

// SUCCESS STORY

const FAMILY_SUCCESS_STORY_NOVEL_DISCOVERY = 'N'
const FAMILY_SUCCESS_STORY_ALTERED_CLINICAL_OUTCOME = 'A'
const FAMILY_SUCCESS_STORY_COLLABORATION = 'C'
const FAMILY_SUCCESS_STORY_TECHNICAL_WIN = 'T'
const FAMILY_SUCCESS_STORY_DATA_SHARING = 'D'
const FAMILY_SUCCESS_STORY_OTHER = 'O'

export const FAMILY_SUCCESS_STORY_TYPE_OPTIONS = [
  { value: FAMILY_SUCCESS_STORY_NOVEL_DISCOVERY, color: '#019143', name: 'Novel Discovery' },
  { value: FAMILY_SUCCESS_STORY_ALTERED_CLINICAL_OUTCOME, color: '#FFAB57', name: 'Altered Clinical Outcome' },
  { value: FAMILY_SUCCESS_STORY_COLLABORATION, color: '#833E7D', name: 'Collaboration' },
  { value: FAMILY_SUCCESS_STORY_TECHNICAL_WIN, color: '#E76013', name: 'Technical Win' },
  { value: FAMILY_SUCCESS_STORY_DATA_SHARING, color: '#6583EC', name: 'Data Sharing' },
  { value: FAMILY_SUCCESS_STORY_OTHER, color: '#5D5D5F', name: 'Other' },
]

export const FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP = FAMILY_SUCCESS_STORY_TYPE_OPTIONS.reduce(
  (acc, tag) => ({ [tag.value]: tag, ...acc }), {},
)

export const successStoryTypeDisplay = tag => (
  <span>
    <ColoredIcon name="stop" color={FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP[tag].color} />
    {FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP[tag].name}
  </span>
)

// FAMILY FIELDS

export const FAMILY_FIELD_ID = 'familyId'
export const FAMILY_DISPLAY_NAME = 'displayName'
export const FAMILY_FIELD_DESCRIPTION = 'description'
export const FAMILY_FIELD_ANALYSIS_STATUS = 'analysisStatus'
export const FAMILY_FIELD_ASSIGNED_ANALYST = 'assignedAnalyst'
export const FAMILY_FIELD_ANALYSED_BY = 'analysedBy'
export const FAMILY_FIELD_SUCCESS_STORY_TYPE = 'successStoryTypes'
export const FAMILY_FIELD_SUCCESS_STORY = 'successStory'
export const FAMILY_FIELD_ANALYSIS_NOTES = 'analysisNotes'
export const FAMILY_FIELD_CASE_NOTES = 'caseNotes'
export const FAMILY_FIELD_MME_NOTES = 'mmeNotes'
export const FAMILY_FIELD_INTERNAL_NOTES = 'caseReviewNotes'
export const FAMILY_FIELD_INTERNAL_SUMMARY = 'caseReviewSummary'
export const FAMILY_FIELD_FIRST_SAMPLE = 'firstSample'
export const FAMILY_FIELD_CODED_PHENOTYPE = 'codedPhenotype'
export const FAMILY_FIELD_MONDO_ID = 'mondoId'
export const FAMILY_FIELD_DISCOVERY_MONDO_ID = 'postDiscoveryMondoId'
export const FAMILY_FIELD_OMIM_NUMBERS = 'postDiscoveryOmimNumbers'
export const FAMILY_FIELD_PMIDS = 'pubmedIds'
export const FAMILY_FIELD_PEDIGREE = 'pedigreeImage'
export const FAMILY_FIELD_CREATED_DATE = 'createdDate'
export const FAMILY_FIELD_ANALYSIS_GROUPS = 'analysisGroups'
export const FAMILY_FIELD_SAVED_VARIANTS = 'savedVariants'
export const FAMILY_FIELD_EXTERNAL_DATA = 'externalData'

export const FAMILY_NOTES_FIELDS = [
  { id: FAMILY_FIELD_CASE_NOTES, noteType: 'C' },
  { id: FAMILY_FIELD_ANALYSIS_NOTES, noteType: 'A' },
  { id: FAMILY_FIELD_MME_NOTES, noteType: 'M' },
]

export const FAMILY_MAIN_FIELDS = [
  { id: FAMILY_FIELD_ANALYSIS_GROUPS },
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSIS_STATUS },
  { id: FAMILY_FIELD_ASSIGNED_ANALYST },
]

export const FAMILY_DETAIL_FIELDS = [
  ...FAMILY_MAIN_FIELDS,
  { id: FAMILY_FIELD_ANALYSED_BY },
  { id: FAMILY_FIELD_EXTERNAL_DATA },
  { id: FAMILY_FIELD_SUCCESS_STORY_TYPE },
  { id: FAMILY_FIELD_SUCCESS_STORY },
  ...FAMILY_NOTES_FIELDS,
  { id: FAMILY_FIELD_CODED_PHENOTYPE },
  { id: FAMILY_FIELD_MONDO_ID },
  { id: FAMILY_FIELD_DISCOVERY_MONDO_ID },
  { id: FAMILY_FIELD_OMIM_NUMBERS },
  { id: FAMILY_FIELD_PMIDS },
]

export const FAMILY_FIELD_NAME_LOOKUP = {
  ...FAMILY_DETAIL_FIELDS.reduce((acc, field) => ({ ...acc, [field.id]: camelcaseToTitlecase(field.id) }), {}),
  [FAMILY_FIELD_DESCRIPTION]: 'Family Description',
  [FAMILY_FIELD_FIRST_SAMPLE]: 'Data Loaded?',
  [FAMILY_FIELD_MME_NOTES]: 'Matchmaker Notes',
  [FAMILY_FIELD_CODED_PHENOTYPE]: 'Phenotype Description',
  [FAMILY_FIELD_MONDO_ID]: 'MONDO ID',
  [FAMILY_FIELD_DISCOVERY_MONDO_ID]: 'Post-discovery MONDO ID',
  [FAMILY_FIELD_OMIM_NUMBERS]: 'Post-discovery OMIM #',
  [FAMILY_FIELD_PMIDS]: 'Publications on this discovery',
  [FAMILY_FIELD_INTERNAL_NOTES]: 'Internal Notes',
  [FAMILY_FIELD_INTERNAL_SUMMARY]: 'Internal Summary',
}

const SHOW_DATA_LOADED = 'SHOW_DATA_LOADED'
const SHOW_ASSIGNED_TO_ME = 'SHOW_ASSIGNED_TO_ME'
const SHOW_ANALYSED_BY_ME = 'SHOW_ANALYSED_BY_ME'
const SHOW_ANALYSED = 'SHOW_ANALYSED'
const SHOW_NOT_ANALYSED = 'SHOW_NOT_ANALYSED'

const hasMatchingSampleFilter = isMatchingSample => (family, user, samplesByFamily) => (
  (family.sampleTypes || samplesByFamily[family.familyGuid] || []).some(
    sample => sample.isActive && isMatchingSample(sample),
  ))

export const ASSIGNED_TO_ME_FILTER = {
  value: SHOW_ASSIGNED_TO_ME,
  name: 'Assigned To Me',
  createFilter: (family, user) => (
    family.assignedAnalyst ? family.assignedAnalyst.email === user.email : null),
}

export const CATEGORY_FAMILY_FILTERS = {
  [FAMILY_FIELD_ANALYSIS_STATUS]: [
    ...SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS.map(option => ({
      ...option,
      createFilter: family => family.analysisStatus === option.value,
    })),
  ],
  [FAMILY_FIELD_ANALYSED_BY]: [
    ASSIGNED_TO_ME_FILTER,
    {
      value: SHOW_ANALYSED_BY_ME,
      name: 'Analysed By Me',
      analysedByFilter: ({ createdBy }, user) => createdBy === (user.displayName || user.email),
    },
    {
      value: SHOW_ANALYSED,
      name: 'Analysed',
      analysedByFilter: () => true,
    },
    {
      value: SHOW_NOT_ANALYSED,
      name: 'Not Analysed',
      requireNoAnalysedBy: true,
      analysedByFilter: () => true,
    },
    ...FAMILY_ANALYSED_BY_DATA_TYPES.map(([type, typeDisplay]) => ({
      value: type,
      name: typeDisplay,
      category: 'Data Type',
      analysedByFilter: ({ dataType }) => dataType === type,
    })),
    {
      value: 'yearSinceAnalysed',
      name: '>1 Year',
      category: 'Analysis Date',
      requireNoAnalysedBy: true,
      analysedByFilter: ({ lastModifiedDate }) => (
        (new Date()).setFullYear(new Date().getFullYear() - 1) < new Date(lastModifiedDate)
      ),
    },
  ],
  [FAMILY_FIELD_FIRST_SAMPLE]: [
    {
      value: SHOW_DATA_LOADED,
      name: 'Data Loaded',
      createFilter: hasMatchingSampleFilter(() => true),
    },
    {
      value: `${SHOW_DATA_LOADED}_RNA`,
      name: 'Data Loaded - RNA',
      createFilter: family => family.hasRna,
    },
    ...[DATASET_TYPE_SV_CALLS, DATASET_TYPE_MITO_CALLS].map(dataType => ({
      value: `${SHOW_DATA_LOADED}_${dataType}`,
      name: `Data Loaded -${DATASET_TITLE_LOOKUP[dataType]}`,
      createFilter: hasMatchingSampleFilter(
        ({ datasetType }) => datasetType === dataType,
      ),
    })),
    {
      value: `${SHOW_DATA_LOADED}_PHENO`,
      name: 'Data Loaded - Phenotype Prioritization',
      createFilter: family => family.hasPhenotypePrioritization,
    },
  ],
}

// INDIVIDUAL FIELDS
const SEX_MALE = 'M'
const SEX_FEMALE = 'F'
const SEX_UNKNOWN = 'U'
const MALE_ANEUPLOIDIES = ['XXY', 'XYY']
const FEMALE_ANEUPLOIDIES = ['XXX', 'X0']
export const SEX_OPTIONS = [
  { value: 'M', text: 'Male' },
  { value: 'F', text: 'Female' },
  { value: 'U', text: '?' },
  ...MALE_ANEUPLOIDIES.map(value => ({ value, text: `Male (${value})` })),
  ...FEMALE_ANEUPLOIDIES.map(value => ({ value, text: `Female (${value})` })),
]

export const SIMPLIFIED_SEX_LOOKUP = {
  ...[SEX_MALE, ...MALE_ANEUPLOIDIES].reduce((acc, val) => ({ ...acc, [val]: SEX_MALE }), {}),
  ...[SEX_FEMALE, ...FEMALE_ANEUPLOIDIES].reduce((acc, val) => ({ ...acc, [val]: SEX_FEMALE }), {}),
  [SEX_UNKNOWN]: SEX_UNKNOWN,
}

export const SEX_LOOKUP = SEX_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.text === '?' ? 'Unknown' : opt.text },
  }), {},
)

export const AFFECTED = 'A'
export const UNAFFECTED = 'N'
export const UNKNOWN_AFFECTED = 'U'
export const AFFECTED_OPTIONS = [
  { value: AFFECTED, text: 'Affected' },
  { value: UNAFFECTED, text: 'Unaffected' },
  { value: UNKNOWN_AFFECTED, text: '?' },
]

export const AFFECTED_LOOKUP = AFFECTED_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.text === '?' ? 'Unknown' : opt.text },
  }), {},
)

export const PROBAND_RELATIONSHIP_OPTIONS = [
  { value: 'S', name: 'Self' },
  { value: 'M', name: 'Mother' },
  { value: 'F', name: 'Father' },
  { value: 'B', name: 'Sibling' },
  { value: 'C', name: 'Child' },
  { value: 'H', name: 'Maternal Half Sibling' },
  { value: 'J', name: 'Paternal Half Sibling' },
  { value: 'G', name: 'Maternal Grandmother' },
  { value: 'W', name: 'Maternal Grandfather' },
  { value: 'X', name: 'Paternal Grandmother' },
  { value: 'Y', name: 'Paternal Grandfather' },
  { value: 'A', name: 'Maternal Aunt' },
  { value: 'L', name: 'Maternal Uncle' },
  { value: 'E', name: 'Paternal Aunt' },
  { value: 'D', name: 'Paternal Uncle' },
  { value: 'N', name: 'Niece' },
  { value: 'P', name: 'Nephew' },
  { value: 'Z', name: 'Maternal 1st Cousin' },
  { value: 'K', name: 'Paternal 1st Cousin' },
  { value: 'O', name: 'Other' },
  { value: 'U', name: 'Unknown' },
]

const PROBAND_RELATIONSHIP_LOOKUP = PROBAND_RELATIONSHIP_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.name },
  }), {},
)

const ANALYTE_TYPE_OPTIONS = [
  { value: 'D', text: 'DNA' },
  { value: 'R', text: 'RNA' },
  { value: 'B', text: 'blood plasma' },
  { value: 'F', text: 'frozen whole blood' },
  { value: 'H', text: 'high molecular weight DNA' },
  { value: 'U', text: 'urine' },
]

const ANALYTE_TYPE_LOOKUP = ANALYTE_TYPE_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.text },
  }), {},
)

const BIOSAMPLE_OPTIONS = [
  { value: 'T', text: 'UBERON:0000479 (tissue)' },
  { value: 'NT', text: 'UBERON:0003714 (neural tissue)' },
  { value: 'S', text: 'UBERON:0001836 (saliva)' },
  { value: 'SE', text: 'UBERON:0001003 (skin epidermis)' },
  { value: 'MT', text: 'UBERON:0002385 (muscle tissue)' },
  { value: 'WB', text: 'UBERON:0000178 (whole blood)' },
  { value: 'BM', text: 'UBERON:0002371 (bone marrow)' },
  { value: 'CC', text: 'UBERON:0006956 (buccal mucosa)' },
  { value: 'CF', text: 'UBERON:0001359 (cerebrospinal fluid)' },
  { value: 'U', text: 'UBERON:0001088 (urine)' },
  { value: 'NE', text: 'UBERON:0019306 (nose epithelium)' },
  { value: 'EM', text: 'UBERON:0005291 (embryonic tissue)' },
  { value: 'CE', text: 'UBERON:0002037 (cerebellum tissue)' },
  { value: 'CA', text: 'UBERON:0001133 (cardiac tissue)' },
  { value: 'IP', text: 'CL:0000034 (iPSC)' },
  { value: 'NP', text: 'CL:0011020 (iPSC NPC)' },
  { value: 'MO', text: 'CL:0000576 (monocytes - PBMCs)' },
  { value: 'LY', text: 'CL:0000542 (lymphocytes - LCLs)' },
  { value: 'FI', text: 'CL:0000057 (fibroblasts)' },
]

const BIOSAMPLE_LOOKUP = BIOSAMPLE_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt.text },
  }), {},
)

export const INDIVIDUAL_FIELD_ID = 'individualId'
export const INDIVIDUAL_FIELD_PATERNAL_ID = 'paternalId'
export const INDIVIDUAL_FIELD_MATERNAL_ID = 'maternalId'
export const INDIVIDUAL_FIELD_SEX = 'sex'
export const INDIVIDUAL_FIELD_AFFECTED = 'affected'
export const INDIVIDUAL_FIELD_NOTES = 'notes'
export const INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP = 'probandRelationship'
export const INDIVIDUAL_FIELD_FEATURES = 'features'
export const INDIVIDUAL_FIELD_FILTER_FLAGS = 'filterFlags'
export const INDIVIDUAL_FIELD_POP_FILTERS = 'popPlatformFilters'
export const INDIVIDUAL_FIELD_SV_FLAGS = 'svFlags'
export const INDIVIDUAL_FIELD_ANALYTE_TYPE = 'analyteType'
export const INDIVIDUAL_FIELD_PRIMARY_BIOSAMPLE = 'primaryBiosample'
export const INDIVIDUAL_FIELD_TISSUE_AFFECTED = 'tissueAffectedStatus'

export const INDIVIDUAL_FIELD_CONFIGS = {
  [FAMILY_FIELD_ID]: { label: 'Family ID' },
  [INDIVIDUAL_FIELD_ID]: { label: 'Individual ID' },
  [INDIVIDUAL_FIELD_PATERNAL_ID]: { label: 'Paternal ID', description: 'Individual ID of the father' },
  [INDIVIDUAL_FIELD_MATERNAL_ID]: { label: 'Maternal ID', description: 'Individual ID of the mother' },
  [INDIVIDUAL_FIELD_SEX]: {
    label: 'Sex',
    format: sex => SEX_LOOKUP[sex],
    width: 3,
    description: 'Male, Female, or Unknown',
    formFieldProps: { component: Select, options: SEX_OPTIONS },
  },
  [INDIVIDUAL_FIELD_AFFECTED]: {
    label: 'Affected Status',
    format: affected => AFFECTED_LOOKUP[affected],
    width: 4,
    description: 'Affected, Unaffected, or Unknown',
    formFieldProps: { component: RadioGroup, options: AFFECTED_OPTIONS },
  },
  [INDIVIDUAL_FIELD_NOTES]: { label: 'Notes', format: stripMarkdown, description: 'free-text notes related to this individual' },
  [INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP]: {
    label: 'Proband Relation',
    description: `Relationship of the individual to the family proband. Can be one of: ${
      PROBAND_RELATIONSHIP_OPTIONS.map(({ name }) => name).join(', ')}`,
    format: relationship => PROBAND_RELATIONSHIP_LOOKUP[relationship],
    formFieldProps: { component: Select, options: PROBAND_RELATIONSHIP_OPTIONS, search: true },
  },
  [INDIVIDUAL_FIELD_ANALYTE_TYPE]: {
    label: 'Analyte Type',
    description: `One of: ${ANALYTE_TYPE_OPTIONS.map(({ text }) => text).join(', ')}`,
    format: val => ANALYTE_TYPE_LOOKUP[val],
    formFieldProps: { component: Select, options: ANALYTE_TYPE_OPTIONS },
  },
  [INDIVIDUAL_FIELD_PRIMARY_BIOSAMPLE]: {
    label: 'Primary Biosample',
    description: `One of: ${BIOSAMPLE_OPTIONS.map(({ text }) => text).join(', ')}`,
    format: val => BIOSAMPLE_LOOKUP[val],
    formFieldProps: { component: Select, options: BIOSAMPLE_OPTIONS },
  },
  [INDIVIDUAL_FIELD_TISSUE_AFFECTED]: {
    label: 'Tissue Affected Status',
    description: 'Yes, No, or Unknown',
    format: val => ({ [true]: 'Yes', [false]: 'No' }[val] || 'Unknown'),
  },
}

export const INDIVIDUAL_HPO_EXPORT_DATA = [
  {
    header: 'HPO Terms (present)',
    field: INDIVIDUAL_FIELD_FEATURES,
    format: features => (features ? features.map(feature => `${feature.id} (${feature.label})`).join('; ') : ''),
    description: 'comma-separated list of HPO Terms for present phenotypes in this individual',
  },
  {
    header: 'HPO Terms (absent)',
    field: 'absentFeatures',
    format: features => (features ? features.map(feature => `${feature.id} (${feature.label})`).join('; ') : ''),
    description: 'comma-separated list of HPO Terms for phenotypes not present in this individual',
  },
]

export const exportConfigForField = fieldConfigs => (field) => {
  const { label, format, description } = fieldConfigs[field]
  return { field, header: label, format, description }
}

export const INDIVIDUAL_HAS_DATA_FIELD = 'hasLoadedSamples'
export const INDIVIDUAL_ID_EXPORT_DATA = [
  FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID,
].map(exportConfigForField(INDIVIDUAL_FIELD_CONFIGS))

const INDIVIDUAL_HAS_DATA_EXPORT_CONFIG = {
  field: INDIVIDUAL_HAS_DATA_FIELD,
  header: 'Individual Data Loaded',
  format: hasData => (hasData ? 'Yes' : 'No'),
}

export const INDIVIDUAL_CORE_EXPORT_DATA = [
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
  INDIVIDUAL_FIELD_NOTES,
].map(exportConfigForField(INDIVIDUAL_FIELD_CONFIGS))

export const INDIVIDUAL_EXPORT_DATA = [].concat(
  INDIVIDUAL_ID_EXPORT_DATA, INDIVIDUAL_CORE_EXPORT_DATA, [INDIVIDUAL_HAS_DATA_EXPORT_CONFIG],
  INDIVIDUAL_HPO_EXPORT_DATA,
)

const FLAG_TITLE = {
  chimera: '% Chimera',
  contamination: '% Contamination',
  coverage_exome: '% 20X Coverage',
  coverage_genome: 'Mean Coverage',
}

const ratioLabel = (flag) => {
  const words = snakecaseToTitlecase(flag).split(' ')
  return `Ratio ${words[1]}/${words[2]}`
}

export const INDIVIDUAL_FIELD_LOOKUP = {
  [INDIVIDUAL_FIELD_FILTER_FLAGS]: {
    fieldDisplay: filterFlags => Object.entries(filterFlags).map(([flag, val]) => (
      <Label
        key={flag}
        basic
        horizontal
        color="orange"
        content={`${FLAG_TITLE[flag] || snakecaseToTitlecase(flag)}: ${parseFloat(val).toFixed(2)}`}
      />
    )),
  },
  [INDIVIDUAL_FIELD_POP_FILTERS]: {
    fieldDisplay: filterFlags => Object.keys(filterFlags).map(flag => (
      <Label
        key={flag}
        basic
        horizontal
        color="orange"
        content={flag.startsWith('r_') ? ratioLabel(flag) : snakecaseToTitlecase(flag.replace('n_', 'num._'))}
      />
    )),
  },
  [INDIVIDUAL_FIELD_SV_FLAGS]: {
    fieldDisplay: filterFlags => filterFlags.map(flag => (
      <Label
        key={flag}
        basic
        horizontal
        color="orange"
        content={snakecaseToTitlecase(flag)}
      />
    )),
  },
  [INDIVIDUAL_FIELD_FEATURES]: {
    fieldDisplay: individual => <HpoPanel individual={individual} />,
    individualFields: individual => ({
      initialValues: { ...individual, individualField: 'hpo_terms' },
      fieldValue: individual,
    }),
  },
}

// CLINVAR

const CLINVAR_DEFAULT_PATHOGENICITY = 'no_pathogenic_assertion'
const CLINVAR_MAX_RISK_PATHOGENICITY = 'established_risk_allele'
const CLINVAR_MIN_RISK_PATHOGENICITY = 'likely_risk_allele'
const CLINVAR_PATHOGENICITIES = [
  'pathogenic',
  'pathogenic/likely_pathogenic',
  'pathogenic/likely_pathogenic/established_risk_allele',
  'pathogenic/likely_pathogenic/likely_risk_allele',
  'pathogenic/likely_risk_allele',
  'likely_pathogenic',
  'likely_pathogenic/likely_risk_allele',
  CLINVAR_MAX_RISK_PATHOGENICITY,
  CLINVAR_MIN_RISK_PATHOGENICITY,
  'conflicting_interpretations_of_pathogenicity',
  'uncertain_risk_allele',
  'uncertain_significance/uncertain_risk_allele',
  'uncertain_significance',
  CLINVAR_DEFAULT_PATHOGENICITY,
  'likely_benign',
  'benign/likely_benign',
  'benign',
].reverse().reduce((acc, path, i) => ({ ...acc, [path]: i }), {})

const HGMD_SEVERITY = {
  DM: 1.5,
  'DM?': 0.5,
  FPV: 0.5,
  FP: 0.5,
  DFP: 0.5,
  DP: 0.5,
}

// LOCUS LISTS

export const LOCUS_LIST_NAME_FIELD = 'name'
export const LOCUS_LIST_NUM_ENTRIES_FIELD = 'numEntries'
export const LOCUS_LIST_DESCRIPTION_FIELD = 'description'
export const LOCUS_LIST_IS_PUBLIC_FIELD_NAME = 'isPublic'
export const LOCUS_LIST_CREATED_DATE_FIELD_NAME = 'createdDate'
export const LOCUS_LIST_LAST_MODIFIED_FIELD_NAME = 'lastModifiedDate'
export const LOCUS_LIST_CURATOR_FIELD_NAME = 'createdBy'

export const LOCUS_LIST_FIELDS = [
  {
    name: LOCUS_LIST_NAME_FIELD,
    label: 'List Name',
    labelHelp: 'A descriptive name for this gene list',
    validate: value => (value ? undefined : 'Name is required'),
    width: 3,
    isEditable: true,
  },
  { name: LOCUS_LIST_NUM_ENTRIES_FIELD, label: 'Entries', width: 1 },
  {
    name: LOCUS_LIST_DESCRIPTION_FIELD,
    label: 'Description',
    labelHelp: 'Some background on how this list is curated',
    validate: value => (value ? undefined : 'Description is required'),
    width: 9,
    isEditable: true,
  },
  {
    name: LOCUS_LIST_CREATED_DATE_FIELD_NAME,
    label: 'Created Date',
    width: 3,
    fieldDisplay: createdDate => new Date(createdDate).toLocaleString('en-US', { year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }),
  },
  {
    name: LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
    label: 'Last Updated',
    width: 3,
    fieldDisplay: lastModifiedDate => new Date(lastModifiedDate).toLocaleString('en-US', { year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }),
  },
  { name: LOCUS_LIST_CURATOR_FIELD_NAME, label: 'Curator', width: 3 },
  {
    name: LOCUS_LIST_IS_PUBLIC_FIELD_NAME,
    label: 'Public List',
    labelHelp: 'Should other seqr users be able to use this gene list?',
    component: RadioGroup,
    options: [{ value: true, text: 'Yes' }, { value: false, text: 'No' }],
    fieldDisplay: isPublic => (isPublic ? 'Yes' : 'No'),
    width: 2,
    isEditable: true,
  },
]

export const LOCUS_LIST_ITEMS_FIELD = {
  name: 'rawItems',
  label: 'Genes/ Intervals',
  labelHelp: 'A list of genes and intervals. Can be separated by commas or whitespace. Intervals should be in the form <chrom>:<start>-<end>',
  fieldDisplay: () => null,
  isEditable: true,
  component: Form.TextArea,
  rows: 12,
  validate: value => (value ? undefined : 'Genes and/or intervals are required'),
  additionalFormFields: [
    {
      name: 'intervalGenomeVersion',
      component: RadioGroup,
      options: GENOME_VERSION_OPTIONS,
      label: 'Genome Version',
      labelHelp: 'The genome version associated with intervals. Only required if the list contains intervals',
      validate: (value, allValues) => (
        (value || !(allValues.rawItems || '').match(/([^\s-]*):(\d*)-(\d*)/)) ? undefined :
          'Genome version is required for lists with intervals'
      ),
    },
    {
      name: 'ignoreInvalidItems',
      component: BooleanCheckbox,
      label: 'Ignore invalid genes and intervals',
    },
  ],
}

export const VEP_GROUP_NONSENSE = 'nonsense'
export const VEP_GROUP_ESSENTIAL_SPLICE_SITE = 'essential_splice_site'
export const VEP_GROUP_EXTENDED_SPLICE_SITE = 'extended_splice_site'
export const VEP_GROUP_MISSENSE = 'missense'
export const VEP_GROUP_FRAMESHIFT = 'frameshift'
export const VEP_GROUP_INFRAME = 'in_frame'
export const VEP_GROUP_SYNONYMOUS = 'synonymous'
export const VEP_GROUP_OTHER = 'other'
export const VEP_GROUP_SV = 'structural'
export const VEP_GROUP_SV_CONSEQUENCES = 'structural_consequence'
export const VEP_GROUP_SV_NEW = 'new_structural_variants'

export const SV_TYPES = [
  {
    description: 'A deletion called from genome data',
    text: 'Deletion',
    value: 'DEL',
  },
  {
    description: 'A duplication called from genome data',
    text: 'Duplication',
    value: 'DUP',
  },
  {
    description: 'A chromosomal translocation',
    text: 'Translocation',
    value: 'CTX',
  },
  {
    description: 'A copy number polymorphism variant',
    text: 'Copy Number',
    value: 'CNV',
  },
  {
    description: 'A Complex Structural Variant',
    text: 'Complex SV',
    value: 'CPX',
  },
  {
    description: 'A large insertion',
    text: 'Insertion',
    value: 'INS',
  },
  {
    description: 'A large inversion',
    text: 'Inversion',
    value: 'INV',
  },
  {
    description: 'An unresolved structural event',
    text: 'Breakend',
    value: 'BND',
  },
]
const VEP_SV_TYPES = [
  {
    description: 'A deletion called from exome data',
    text: 'Exome Deletion',
    value: 'gCNV_DEL',
  },
  {
    description: 'A duplication called from exome data',
    text: 'Exome Duplication',
    value: 'gCNV_DUP',
  },
  ...SV_TYPES,
]

export const EXTENDED_INTRONIC_DESCRIPTION = "A variant which falls in the first 9 bases of the 5' end of intron or the within the last 9 bases of the 3' end of intron"

const VEP_SV_CONSEQUENCES = [
  {
    description: 'A loss of function effect',
    text: 'Loss of function',
    value: 'LOF',
  },
  {
    description: 'An SV which is predicted to result in intragenic exonic duplication without breaking any coding sequences' +
        ' (previously called "Loss of function via Duplication")',
    text: 'Intragenic Exon Duplication',
    value: 'INTRAGENIC_EXON_DUP',
  },
  {
    description: 'The duplication SV has one breakpoint in the coding sequence',
    text: 'Partial Exon Duplication',
    value: 'PARTIAL_EXON_DUP',
  },
  {
    description: 'A copy-gain effect',
    text: 'Copy Gain',
    value: 'COPY_GAIN',
  },
  {
    description: 'A duplication partially overlapping the gene',
    text: 'Duplication Partial',
    value: 'DUP_PARTIAL',
  },
  {
    description: 'A multiallelic SV would be predicted to have a Loss of function, Intragenic Exon Duplication, Copy Gain,' +
        ' Duplication Partial, Duplication at the Transcription Start Site (TSS_DUP), or Duplication with a breakpoint' +
        ' in the coding sequence annotation if the SV were biallelic',
    text: 'Multiallelic SV',
    value: 'MSV_EXON_OVERLAP',
  },
  {
    description: 'An SV contained entirely within an intron',
    text: 'Intronic',
    value: 'INTRONIC',
  },
  {
    description: 'An inversion entirely spanning the gene',
    text: 'Inversion Span',
    value: 'INV_SPAN',
  },
  {
    description: 'An SV which disrupts an untranslated region',
    text: 'UTR',
    value: 'UTR',
  },
  {
    description: 'An SV which disrupts a promoter sequence (within 1kb)',
    text: 'Promoter',
    value: 'PROMOTER',
  },
  {
    description: 'An SV which the SV breakend is predicted to fall in an exon',
    text: 'Breakend Exonic',
    value: 'BREAKEND_EXONIC',
  },
  {
    description: 'An SV is predicted to duplicate the transcription start site',
    text: 'Transcription Start Site Duplication',
    value: 'TSS_DUP',
  },
]

const SV_NEW_OPTIONS = [
  {
    description: 'An SV with no overlap in a previous callset',
    text: 'New Calls Only',
    value: 'NEW',
  },
]

const ORDERED_VEP_CONSEQUENCES = [
  {
    description: 'A feature ablation whereby the deleted region includes a transcript feature',
    text: 'Transcript ablation',
    value: 'transcript_ablation',
    so: 'SO:0001893',
  },
  {
    description: "A splice variant that changes the 2 base region at the 5' end of an intron",
    text: 'Splice donor variant',
    value: 'splice_donor_variant',
    group: VEP_GROUP_ESSENTIAL_SPLICE_SITE,
    so: 'SO:0001575',
  },
  {
    description: "A splice variant that changes the 2 base region at the 3' end of an intron",
    text: 'Splice acceptor variant',
    value: 'splice_acceptor_variant',
    group: VEP_GROUP_ESSENTIAL_SPLICE_SITE,
    so: 'SO:0001574',
  },
  {
    description: 'A sequence variant whereby at least one base of a codon is changed, resulting in a premature stop codon, leading to a shortened transcript',
    text: 'Stop gained',
    value: 'stop_gained',
    group: VEP_GROUP_NONSENSE,
    so: 'SO:0001587',
  },
  {
    description: 'A sequence variant which causes a disruption of the translational reading frame, because the number of nucleotides inserted or deleted is not a multiple of three',
    text: 'Frameshift',
    value: 'frameshift_variant',
    group: VEP_GROUP_FRAMESHIFT,
    so: 'SO:0001589',
  },
  ...VEP_SV_TYPES.map(v => ({ ...v, group: VEP_GROUP_SV })),
  ...VEP_SV_CONSEQUENCES.map(v => ({ ...v, group: VEP_GROUP_SV_CONSEQUENCES })),
  {
    description: 'A sequence variant where at least one base of the terminator codon (stop) is changed, resulting in an elongated transcript',
    text: 'Stop lost',
    value: 'stop_lost',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001578',
  },
  {
    description: 'A codon variant that changes at least one base of the canonical start codon.',
    text: 'Start lost',
    value: 'start_lost',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0002012',
  },
  {
    description: 'An inframe non synonymous variant that inserts bases into in the coding sequence',
    text: 'In frame insertion',
    value: 'inframe_insertion',
    group: VEP_GROUP_INFRAME,
    so: 'SO:0001821',
  },
  {
    description: 'An inframe non synonymous variant that deletes bases from the coding sequence',
    text: 'In frame deletion',
    value: 'inframe_deletion',
    group: VEP_GROUP_INFRAME,
    so: 'SO:0001822',
  },
  {
    description: 'A sequence_variant which is predicted to change the protein encoded in the coding sequence',
    text: 'Protein Altering',
    value: 'protein_altering_variant',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001818',
  },
  {
    description: 'A sequence variant, where the change may be longer than 3 bases, and at least one base of a codon is changed resulting in a codon that encodes for a different amino acid',
    text: 'Missense',
    value: 'missense_variant',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001583',
  },
  {
    description: 'A sequence variant that causes a change at the 5th base pair after the start of the intron in the orientation of the transcript',
    text: 'Splice donor 5th base',
    value: 'splice_donor_5th_base_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
    so: 'SO:0001787',
  },
  {
    description: 'A sequence variant in which a change has occurred within the region of the splice site, either within 1-3 bases of the exon or 3-8 bases of the intron',
    text: 'Splice region',
    value: 'splice_region_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
    so: 'SO:0001630',
  },
  {
    description: "A sequence variant that falls in the region between the 3rd and 6th base after splice junction (5' end of intron)",
    text: 'Splice donor region',
    value: 'splice_donor_region_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
    so: 'SO:0002170',
  },
  {
    description: "A sequence variant that falls in the polypyrimidine tract at 3' end of intron between 17 and 3 bases from the end (acceptor -3 to acceptor -17)",
    text: 'Splice polypyrimidine tract',
    value: 'splice_polypyrimidine_tract_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
    so: 'SO:0002169',
  },
  {
    description: EXTENDED_INTRONIC_DESCRIPTION,
    text: 'Extended Intronic Splice Region',
    value: 'extended_intronic_splice_region_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
  },
  {
    description: 'A sequence variant where at least one base of the final codon of an incompletely annotated transcript is changed',
    text: 'Incomplete terminal codon variant',
    value: 'incomplete_terminal_codon_variant',
    so: 'SO:0001626',
  },
  {
    description: 'A sequence variant where there is no resulting change to the encoded amino acid',
    text: 'Synonymous',
    value: 'synonymous_variant',
    group: VEP_GROUP_SYNONYMOUS,
    so: 'SO:0001819',
  },
  {
    description: 'A sequence variant where at least one base in the start codon is changed, but the start remains',
    text: 'Start retained',
    value: 'start_retained_variant',
    group: VEP_GROUP_SYNONYMOUS,
    so: 'SO:0002019',
  },
  {
    description: 'A sequence variant where at least one base in the terminator codon is changed, but the terminator remains',
    text: 'Stop retained',
    value: 'stop_retained_variant',
    group: VEP_GROUP_SYNONYMOUS,
    so: 'SO:0001567',
  },
  {
    description: 'A sequence variant that changes the coding sequence',
    text: 'Coding sequence variant',
    value: 'coding_sequence_variant',
    so: 'SO:0001580',
  },
  {
    description: 'A transcript variant located with the sequence of the mature miRNA',
    text: 'Mature miRNA variant',
    value: 'mature_miRNA_variant',
    so: 'SO:0001620',
  },
  {
    description: "A UTR variant of the 5' UTR",
    text: '5 prime UTR variant',
    value: '5_prime_UTR_variant',
    so: 'SO:0001623',
  },
  {
    description: "A UTR variant of the 3' UTR",
    text: '3 prime UTR variant',
    value: '3_prime_UTR_variant',
    so: 'SO:0001624',
  },
  {
    description: 'A transcript variant occurring within an intron',
    text: 'Intron variant',
    value: 'intron_variant',
    so: 'SO:0001627',
  },
  {
    description: 'A variant in a transcript that is the target of NMD',
    text: 'NMD transcript variant',
    value: 'NMD_transcript_variant',
    so: 'SO:0001621',
  },
  {
    description: 'A sequence variant that changes non-coding exon sequence in a canonical transcript for that gene, typically a noncoding gene',
    text: 'Non-coding transcript exon variant (canonical)',
    value: 'non_coding_transcript_exon_variant__canonical',
  },
  {
    description: 'A sequence variant that changes non-coding exon sequence in any transcript for that gene, often a noncoding version of a protein coding gene',
    text: 'Non-coding transcript exon variant (all)',
    value: 'non_coding_transcript_exon_variant',
    so: 'SO:0001792',
  },
  {
    description: 'A transcript variant of a non coding RNA',
    text: 'Non-coding transcript variant',
    value: 'non_coding_transcript_variant',
    so: 'SO:0001619',
  },
  {
    description: 'A transcript variant of a protein coding gene',
    text: 'Coding transcript variant',
    value: 'coding_transcript_variant',
    so: 'SO:0001968',
  },
  {
    description: 'A sequence variant located in the intergenic region, between genes',
    text: 'Intergenic variant',
    value: 'intergenic_variant',
    so: 'SO:0001628',
  },
  {
    description: 'A sequence_variant is a non exact copy of a sequence_feature or genome exhibiting one or more sequence_alteration',
    text: 'Sequence variant',
    value: 'sequence_variant',
    so: 'SO:0001060',
  },
]

export const GROUPED_VEP_CONSEQUENCES = ORDERED_VEP_CONSEQUENCES.reduce((acc, consequence) => {
  const group = consequence.group || VEP_GROUP_OTHER
  acc[group] = [...(acc[group] || []), consequence]
  return acc
}, { [VEP_GROUP_SV_NEW]: SV_NEW_OPTIONS })

export const VEP_CONSEQUENCE_ORDER_LOOKUP = ORDERED_VEP_CONSEQUENCES.reduce(
  (acc, consequence, i) => ({ ...acc, [consequence.value]: i }), {},
)

export const SVTYPE_LOOKUP = VEP_SV_TYPES.reduce((acc, { value, text }) => ({ ...acc, [value]: text }), {})

export const SVTYPE_DETAILS = {
  CPX: {
    INS_iDEL: 'Insertion with deletion at insertion site',
    INVdel: 'Complex inversion with 3\' flanking deletion',
    INVdup: 'Complex inversion with 3\' flanking duplication',
    dDUP: 'Dispersed duplication',
    dDUP_iDEL: 'Dispersed duplication with deletion at insertion site',
    delINV: 'Complex inversion with 5\' flanking deletion',
    delINVdel: 'Complex inversion with 5\' and 3\' flanking deletions',
    delINVdup: 'Complex inversion with 5\' flanking deletion and 3\' flanking duplication',
    dupINV: 'Complex inversion with 5\' flanking duplication',
    dupINVdel: 'Complex inversion with 5\' flanking duplication and 3\' flanking deletion',
    dupINVdup: 'Complex inversion with 5\' and 3\' flanking duplications',
    piDUP_FR: 'Palindromic inverted tandem duplication, forward-reverse orientation',
    piDUP_RF: 'Palindromic inverted tandem duplication, reverse-forward orientation',
  },
  INS: {
    ME: 'Mobile element',
    'ME:ALU': 'Alu element insertion',
    'ME:LINE1': 'LINE1 element insertion',
    'ME:SVA': 'SVA element insertion',
    'ME:UNK': 'Unspecified origin insertion',
  },
}

export const SCREEN_LABELS = {
  PLS: 'Promotor-like signatures',
  pELS: 'proximal Enhancer-like signatures',
  dELS: 'distal Enhancer-like signatures',
}

export const SHOW_ALL = 'ALL'
export const NOTE_TAG_NAME = 'Has Notes'
export const EXCLUDED_TAG_NAME = 'Excluded'
export const REVIEW_TAG_NAME = 'Review'
export const KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME = 'Known gene for phenotype'
export const DISCOVERY_CATEGORY_NAME = 'CMG Discovery Tags'
export const MME_TAG_NAME = 'MME Submission'
export const GREGOR_FINDING_TAG_NAME = 'GREGoR Finding'

export const SORT_BY_FAMILY_GUID = 'FAMILY_GUID'
export const SORT_BY_XPOS = 'XPOS'
const SORT_BY_PATHOGENICITY = 'PATHOGENICITY'
const SORT_BY_IN_OMIM = 'IN_OMIM'
const SORT_BY_PRIORITIZED_GENE = 'PRIORITIZED_GENE'
const SORT_BY_PROTEIN_CONSQ = 'PROTEIN_CONSEQUENCE'
const SORT_BY_GNOMAD_GENOMES = 'GNOMAD'
const SORT_BY_GNOMAD_EXOMES = 'GNOMAD_EXOMES'
const SORT_BY_CALLSET_AF = 'CALLSET_AF'
const SORT_BY_CONSTRAINT = 'CONSTRAINT'
const SORT_BY_CADD = 'CADD'
const SORT_BY_REVEL = 'REVEL'
const SORT_BY_SPLICE_AI = 'SPLICE_AI'
const SORT_BY_EIGEN = 'EIGEN'
const SORT_BY_MPC = 'MPC'
const SORT_BY_PRIMATE_AI = 'PRIMATE_AI'
const SORT_BY_ALPHAMISSENSE = 'ALPHAMISSENSE'
const SORT_BY_TAGGED_DATE = 'TAGGED_DATE'
const SORT_BY_SIZE = 'SIZE'

export const getPermissionedHgmdClass = (variant, user, familiesByGuid, projectByGuid) => (
  user.isAnalyst || variant.familyGuids.some(
    familyGuid => projectByGuid[familiesByGuid[familyGuid].projectGuid].enableHgmd,
  )) && variant.hgmd && variant.hgmd.class

export const clinvarSignificance = (clinvar) => {
  let { pathogenicity, assertions } = clinvar || {}
  const { clinicalSignificance } = clinvar || {}
  if (clinicalSignificance && !pathogenicity) {
    [pathogenicity, ...assertions] = clinicalSignificance.split(/[,|]/)
    if (pathogenicity === 'Pathogenic/Likely_pathogenic/Pathogenic') {
      pathogenicity = 'Pathogenic/Likely_pathogenic'
    } else if (pathogenicity === 'Pathogenic/Pathogenic') {
      pathogenicity = 'Pathogenic'
    }
    if (!(pathogenicity.replace(' ', '_').toLowerCase() in CLINVAR_PATHOGENICITIES)) {
      assertions = [pathogenicity, ...assertions]
      pathogenicity = CLINVAR_DEFAULT_PATHOGENICITY
    }
    assertions = assertions.map(a => a.replace(/^_/, ''))
  }

  return { pathogenicity, assertions, severity: CLINVAR_PATHOGENICITIES[pathogenicity?.replace(' ', '_').toLowerCase()] }
}

export const clinvarColor = (severity, pathColor, riskColor, benignColor) => {
  if (severity > CLINVAR_PATHOGENICITIES[CLINVAR_MAX_RISK_PATHOGENICITY]) {
    return pathColor
  }
  if (severity >= CLINVAR_PATHOGENICITIES[CLINVAR_MIN_RISK_PATHOGENICITY]) {
    return riskColor
  }
  if (severity < CLINVAR_PATHOGENICITIES[CLINVAR_DEFAULT_PATHOGENICITY]) {
    return benignColor
  }
  return null
}

const clinsigSeverity = (variant, user, familiesByGuid, projectByGuid) => {
  const { pathogenicity, severity } = clinvarSignificance(variant.clinvar)
  const hgmdSignificance = getPermissionedHgmdClass(variant, user, familiesByGuid, projectByGuid)
  if (!pathogenicity && !hgmdSignificance) return -10
  const clinvarSeverity = pathogenicity ? severity + 1 : 0.1
  const hgmdSeverity = HGMD_SEVERITY[hgmdSignificance] || 0
  return clinvarSeverity + hgmdSeverity
}

export const MISSENSE_THRESHHOLD = 3
export const LOF_THRESHHOLD = 0.35

const PRIORITIZED_GENE_MAX_RANK = 1000

export const getDecipherGeneLink = ({ geneId }) => `https://www.deciphergenomics.org/gene/${geneId}/overview/protein-genomic-info`

const getGeneConstraintSortScore = ({ constraints }) => {
  if (!constraints || constraints.louef === undefined) {
    return Infinity
  }
  let missenseOffset = constraints.misZ > MISSENSE_THRESHHOLD ? constraints.misZ : 0
  if (constraints.louef > LOF_THRESHHOLD) {
    missenseOffset /= MISSENSE_THRESHHOLD
  }
  return constraints.louef - missenseOffset
}

const populationComparator =
  population => (a, b) => ((a.populations || {})[population] || {}).af - ((b.populations || {})[population] || {}).af

const predictionComparator =
  prediction => (a, b) => ((b.predictions || {})[prediction] || -1) - ((a.predictions || {})[prediction] || -1)

const getTranscriptValues = (transcripts, getValue) => (
  Object.values(transcripts || {}).flat().map(getValue).filter(val => val)
)

const getConsequenceRank = ({ transcripts, svType }) => (
  transcripts ? Math.min(...getTranscriptValues(
    transcripts,
    ({ majorConsequence }) => VEP_CONSEQUENCE_ORDER_LOOKUP[majorConsequence],
  )) : VEP_CONSEQUENCE_ORDER_LOOKUP[svType]
)

const getAlphamissenseRank = ({ transcripts }) => Math.max(
  ...getTranscriptValues(transcripts, t => t.alphamissense?.pathogenicity),
)

const getPrioritizedGeneTopRank = (variant, genesById, individualGeneDataByFamilyGene) => Math.min(...Object.keys(
  variant.transcripts || {},
).reduce((acc, geneId) => (
  genesById[geneId] && individualGeneDataByFamilyGene[variant.familyGuids[0]]?.phenotypeGeneScores ? [
    ...acc,
    ...Object.values(individualGeneDataByFamilyGene[variant.familyGuids[0]].phenotypeGeneScores[geneId] || {}).reduce(
      (acc2, toolScores) => ([...acc2, ...toolScores.map(score => score.rank)]), [],
    ),
  ] : acc), [PRIORITIZED_GENE_MAX_RANK]))

const VARIANT_SORT_OPTONS = [
  { value: SORT_BY_FAMILY_GUID, text: 'Family', comparator: (a, b) => a.familyGuids[0].localeCompare(b.familyGuids[0]) },
  { value: SORT_BY_XPOS, text: 'Position', comparator: (a, b) => a.xpos - b.xpos },
  {
    value: SORT_BY_IN_OMIM,
    text: 'In OMIM',
    comparator: (a, b, genesById) => (
      Object.keys(b.transcripts || {}).reduce(
        (acc, geneId) => (genesById[geneId] ? acc + genesById[geneId].omimPhenotypes.length : acc), 0,
      ) - Object.keys(a.transcripts || {}).reduce(
        (acc, geneId) => (genesById[geneId] ? acc + genesById[geneId].omimPhenotypes.length : acc), 0,
      )),
  },
  {
    value: SORT_BY_PROTEIN_CONSQ,
    text: 'Protein Consequence',
    comparator: (a, b) => getConsequenceRank(a) - getConsequenceRank(b),
  },
  { value: SORT_BY_GNOMAD_GENOMES, text: 'gnomAD Genomes Frequency', comparator: populationComparator('gnomad_genomes') },
  { value: SORT_BY_GNOMAD_EXOMES, text: 'gnomAD Exomes Frequency', comparator: populationComparator('gnomad_exomes') },
  { value: SORT_BY_CALLSET_AF, text: 'Callset AF', comparator: populationComparator('callset') },
  { value: SORT_BY_CADD, text: 'CADD', comparator: predictionComparator('cadd') },
  { value: SORT_BY_REVEL, text: 'REVEL', comparator: predictionComparator('revel') },
  { value: SORT_BY_EIGEN, text: 'Eigen', comparator: predictionComparator('eigen') },
  { value: SORT_BY_MPC, text: 'MPC', comparator: predictionComparator('mpc') },
  { value: SORT_BY_SPLICE_AI, text: 'SpliceAI', comparator: predictionComparator('splice_ai') },
  { value: SORT_BY_PRIMATE_AI, text: 'PrimateAI', comparator: predictionComparator('primate_ai') },
  {
    value: SORT_BY_ALPHAMISSENSE,
    text: 'AlphaMissense',
    comparator: (a, b) => getAlphamissenseRank(b) - getAlphamissenseRank(a),
  },
  {
    value: SORT_BY_PATHOGENICITY,
    text: 'Pathogenicity',
    comparator: (a, b, geneId, tagsByGuid, user, familiesByGuid, projectByGuid) => (
      clinsigSeverity(b, user, familiesByGuid, projectByGuid) - clinsigSeverity(a, user, familiesByGuid, projectByGuid)
    ),
  },
  {
    value: SORT_BY_CONSTRAINT,
    text: 'Constraint',
    comparator: (a, b, genesById) => (
      Math.min(...Object.keys(a.transcripts || {}).reduce(
        (acc, geneId) => [...acc, getGeneConstraintSortScore(genesById[geneId] || {})], [],
      )) - Math.min(...Object.keys(b.transcripts || {}).reduce(
        (acc, geneId) => [...acc, getGeneConstraintSortScore(genesById[geneId] || {})], [],
      ))),
  },
  {
    value: SORT_BY_PRIORITIZED_GENE,
    text: 'Phenotype Prioritized Gene',
    comparator: (a, b, genesById, _tag, _user, _family, _project, individualGeneDataByFamilyGene) => (
      getPrioritizedGeneTopRank(a, genesById, individualGeneDataByFamilyGene) -
        getPrioritizedGeneTopRank(b, genesById, individualGeneDataByFamilyGene)
    ),
  },
  {
    value: SORT_BY_SIZE,
    text: 'Size',
    comparator: (a, b) => ((a.pos - a.end) - (b.pos - b.end)),
  },
  {
    value: SORT_BY_TAGGED_DATE,
    text: 'Last Tagged',
    comparator: (a, b, genesById, tagsByGuid) => (
      b.tagGuids.map(tagGuid => (tagsByGuid[tagGuid] || {}).lastModifiedDate).sort()[b.tagGuids.length - 1] || ''
    ).localeCompare(
      a.tagGuids.map(tagGuid => (tagsByGuid[tagGuid] || {}).lastModifiedDate).sort()[a.tagGuids.length - 1] || '',
    ),
  },
]
const VARIANT_SEARCH_SORT_OPTONS = VARIANT_SORT_OPTONS.slice(0, VARIANT_SORT_OPTONS.length - 1)

export const VARIANT_SORT_LOOKUP = VARIANT_SORT_OPTONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.comparator,
  }), {},
)

const BASE_VARIANT_SORT_FIELD = {
  name: 'sort',
  component: Dropdown,
  inline: true,
  selection: false,
  fluid: false,
  label: 'Sort By:',
}
export const VARIANT_SORT_FIELD = { ...BASE_VARIANT_SORT_FIELD, options: VARIANT_SORT_OPTONS }
export const VARIANT_SEARCH_SORT_FIELD = { ...BASE_VARIANT_SORT_FIELD, options: VARIANT_SEARCH_SORT_OPTONS }
export const VARIANT_HIDE_EXCLUDED_FIELD = {
  name: 'hideExcluded',
  component: InlineToggle,
  label: 'Hide Excluded',
  labelHelp: 'Remove all variants tagged with the "Excluded" tag from the results',
}
export const VARIANT_HIDE_REVIEW_FIELD = {
  name: 'hideReviewOnly',
  component: InlineToggle,
  label: 'Hide Review Only',
  labelHelp: 'Remove all variants tagged with only the "Review" tag from the results',
}
export const VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD = {
  name: 'hideKnownGeneForPhenotype',
  component: InlineToggle,
  label: 'Hide Known Gene For Phenotype',
  labelHelp: 'Remove all variants tagged with the "Known Gene For Phenotype" tag from the results',
}
export const VARIANT_PER_PAGE_FIELD = {
  name: 'recordsPerPage',
  component: Dropdown,
  inline: true,
  selection: false,
  fluid: false,
  label: 'Variants Per Page:',
  options: [{ value: 10 }, { value: 25 }, { value: 50 }, { value: 100 }],
}
export const VARIANT_PAGINATION_FIELD = {
  name: 'page',
  component: Pagination,
  size: 'mini',
  siblingRange: 0,
  firstItem: null,
  lastItem: null,
  format: val => parseInt(val, 10),
}
export const VARIANT_TAGGED_DATE_FIELD = {
  name: 'taggedAfter',
  component: BaseSemanticInput,
  inputType: 'Input',
  label: 'Tagged After',
  type: 'date',
  inline: true,
}

const INDICATOR_MAP = {
  D: { color: 'red', value: 'damaging' },
  T: { color: 'green', value: 'tolerated' },
}

const FATHMM_MAP = {
  ...INDICATOR_MAP,
  N: { color: 'green', value: 'neutral' },
}

const POLYPHEN_MAP = {
  D: { color: 'red', value: 'probably damaging' },
  P: { color: 'yellow', value: 'possibly damaging' },
  B: { color: 'green', value: 'benign' },
}

const MUTTASTER_MAP = {
  D: { color: 'red', value: 'disease causing' },
  A: { color: 'red', value: 'disease causing automatic' },
  N: { color: 'green', value: 'polymorphism' },
  P: { color: 'green', value: 'polymorphism automatic' },
}

const MITOTIP_MAP = {
  likely_pathogenic: { color: 'red', value: 'likely pathogenic' },
  possibly_pathogenic: { color: 'red', value: 'possibly pathogenic' },
  possibly_benign: { color: 'green', value: 'possibly benign' },
  likely_benign: { color: 'green', value: 'likely benign' },
}

const MISSENSE_IN_SILICO_GROUP = 'Missense'
const CODING_IN_SILICO_GROUP = 'Coding/Noncoding'
const SPLICING_IN_SILICO_GROUP = 'Splicing'
export const SV_IN_SILICO_GROUP = 'Structural'
export const NO_SV_IN_SILICO_GROUPS = [MISSENSE_IN_SILICO_GROUP, CODING_IN_SILICO_GROUP]
export const SPLICE_AI_FIELD = 'splice_ai'

const rangeSourceLink = <a href="https://pubmed.ncbi.nlm.nih.gov/36413997" target="_blank" rel="noreferrer">36413997</a>
const PRED_COLOR_MAP = ['green', 'olive', 'grey', 'yellow', 'red', '#8b0000']
const REVERSE_PRED_COLOR_MAP = [...PRED_COLOR_MAP].reverse()

export const ORDERED_PREDICTOR_FIELDS = [
  { field: 'cadd', group: CODING_IN_SILICO_GROUP, thresholds: [0.151, 22.8, 25.3, 28.1, undefined], min: 1, max: 99, fieldTitle: 'CADD', requiresCitation: true },
  { field: 'revel', group: MISSENSE_IN_SILICO_GROUP, thresholds: [0.0161, 0.291, 0.644, 0.773, 0.932], fieldTitle: 'REVEL', requiresCitation: true },
  { field: 'alphamissense', fieldTitle: 'AlphaMissense', displayOnly: true },
  { field: 'vest', thresholds: [undefined, 0.45, 0.764, 0.861, 0.965], fieldTitle: 'VEST', requiresCitation: true },
  { field: 'mut_pred', thresholds: [0.0101, 0.392, 0.737, 0.829, 0.932], fieldTitle: 'MutPred', requiresCitation: true },
  { field: 'mpc', group: MISSENSE_IN_SILICO_GROUP, thresholds: [undefined, undefined, 1.36, 1.828, undefined], max: 5, fieldTitle: 'MPC' },
  {
    field: SPLICE_AI_FIELD,
    group: SPLICING_IN_SILICO_GROUP,
    thresholds: [undefined, undefined, 0.5, 0.8, undefined],
    infoField: 'splice_ai_consequence',
    infoTitle: 'Predicted Consequence',
    fieldTitle: 'SpliceAI',
    getHref: ({ chrom, pos, ref, alt, genomeVersion }) => (
      `https://spliceailookup.broadinstitute.org/#variant=${chrom}-${pos}-${ref}-${alt}&hg=${genomeVersion}&distance=1000&mask=0`
    ),
  },
  { field: 'primate_ai', group: MISSENSE_IN_SILICO_GROUP, thresholds: [undefined, 0.484, 0.79, 0.867, undefined], fieldTitle: 'PrimateAI', requiresCitation: true },
  { field: 'eigen', group: CODING_IN_SILICO_GROUP, thresholds: [undefined, undefined, 1, 2, undefined], max: 99 },
  { field: 'dann', displayOnly: true, thresholds: [undefined, undefined, 0.93, 0.96, undefined] },
  { field: 'strvctvre', group: SV_IN_SILICO_GROUP, thresholds: [undefined, undefined, 0.5, 0.75, undefined] },
  { field: 'polyphen', group: MISSENSE_IN_SILICO_GROUP, thresholds: [undefined, 0.114, 0.978, 0.999, undefined], indicatorMap: POLYPHEN_MAP, fieldTitle: 'PolyPhen', requiresCitation: true },
  { field: 'sift', reverseThresholds: true, thresholds: [undefined, 0, 0.002, 0.081, undefined], group: MISSENSE_IN_SILICO_GROUP, indicatorMap: INDICATOR_MAP, fieldTitle: 'SIFT', requiresCitation: true },
  { field: 'mut_taster', group: MISSENSE_IN_SILICO_GROUP, indicatorMap: MUTTASTER_MAP, fieldTitle: 'MutTaster' },
  { field: 'fathmm', reverseThresholds: true, thresholds: [undefined, -5.041, -4.14, 3.32, undefined], group: MISSENSE_IN_SILICO_GROUP, indicatorMap: FATHMM_MAP, fieldTitle: 'FATHMM', requiresCitation: true },
  { field: 'apogee', thresholds: [undefined, undefined, 0.5, 0.5, undefined] },
  {
    field: 'gnomad_noncoding',
    fieldTitle: 'gnomAD Constraint',
    displayOnly: true,
    thresholds: [undefined, undefined, 2.18, 4, undefined],
    requiresCitation: true,
  },
  { field: 'haplogroup_defining', indicatorMap: { Y: { color: 'green', value: '' } } },
  { field: 'mitotip', indicatorMap: MITOTIP_MAP, fieldTitle: 'MitoTIP' },
  { field: 'hmtvar', thresholds: [undefined, undefined, 0.35, 0.35, undefined], fieldTitle: 'HmtVar' },
  { field: 'mlc', thresholds: [undefined, 0.5, 0.5, 0.75, undefined], fieldTitle: 'MLC' },
]

export const coloredIcon = color => React.createElement(color.startsWith('#') ? ColoredIcon : Icon, { name: 'circle', size: 'small', color })
export const predictionFieldValue = (
  predictions, { field, fieldValue, thresholds, reverseThresholds, indicatorMap, infoField, infoTitle },
) => {
  let value = fieldValue || predictions[field]
  if (value === null || value === undefined) {
    return { value }
  }

  const infoValue = predictions[infoField]

  const floatValue = parseFloat(value)
  if (thresholds && !(indicatorMap && Number.isNaN(floatValue))) {
    value = floatValue.toPrecision(3)
    const color = (reverseThresholds ? REVERSE_PRED_COLOR_MAP : PRED_COLOR_MAP).find(
      (clr, i) => (thresholds[i - 1] || thresholds[i]) &&
        (thresholds[i - 1] === undefined || value >= thresholds[i - 1]) &&
        (thresholds[i] === undefined || value < thresholds[i]),
    )
    return { value, color, infoValue, infoTitle, thresholds, reverseThresholds }
  }

  return indicatorMap[value[0]] || indicatorMap[value]
}
export const predictorColorRanges = (thresholds, requiresCitation, reverseThresholds) => (
  <div>
    {(reverseThresholds ? REVERSE_PRED_COLOR_MAP : PRED_COLOR_MAP).map((c, i) => {
      const prevUndefined = thresholds[i - 1] === undefined
      let range
      if (thresholds[i] === undefined) {
        if (prevUndefined) {
          return null
        }
        range = ` >= ${thresholds[i - 1]}`
      } else if (prevUndefined) {
        range = ` < ${thresholds[i]}`
      } else if (thresholds[i - 1] === thresholds[i]) {
        return null
      } else {
        range = ` ${thresholds[i - 1]} - ${thresholds[i]}`
      }
      return (
        <div key={c}>
          {coloredIcon(c)}
          {range}
        </div>
      )
    })}
    {requiresCitation && (
      <small>
        {/* eslint-disable-next-line react/jsx-one-expression-per-line */}
        Based on 2022 ClinGen recommendations (PMID:&nbsp;{rangeSourceLink})
      </small>
    )}
  </div>
)

export const getVariantMainGeneId = ({ transcripts = {}, mainTranscriptId, selectedMainTranscriptId }) => {
  if (selectedMainTranscriptId || mainTranscriptId) {
    return (Object.entries(transcripts).find(
      entry => entry[1].some(({ transcriptId }) => transcriptId === (selectedMainTranscriptId || mainTranscriptId)),
    ) || [])[0]
  }
  const transcriptList = Object.values(transcripts)
  if (Object.keys(transcripts).length === 1 && transcriptList[0] && transcriptList[0].length === 0) {
    return Object.keys(transcripts)[0]
  }
  return null
}

export const getVariantMainTranscript = ({ transcripts = {}, mainTranscriptId, selectedMainTranscriptId }) => flatten(
  Object.values(transcripts),
).find(({ transcriptId }) => transcriptId === (selectedMainTranscriptId || mainTranscriptId)) || {}

export const getVariantSummary = (variant, individualGuid) => {
  const { alt, ref, chrom, pos, end, genomeVersion } = variant
  const mainTranscript = getVariantMainTranscript(variant)
  let consequence = `${(mainTranscript.majorConsequence || '').replace(/_variant/g, '').replace(/_/g, ' ')} variant`
  let variantDetail = [(mainTranscript.hgvsc || '').split(':').pop(), (mainTranscript.hgvsp || '').split(':').pop()].filter(val => val).join('/')
  const displayGenomeVersion = GENOME_VERSION_DISPLAY_LOOKUP[genomeVersion] || genomeVersion
  let inheritance = ''
  if (individualGuid) {
    const genotype = (variant.genotypes || {})[individualGuid] || {}
    inheritance = genotype.numAlt === 1 ? ' heterozygous' : ' homozygous'
    if (genotype.numAlt === -1) {
      inheritance = ' copy number'
      consequence = genotype.cn < 2 ? 'deletion' : 'duplication'
      variantDetail = `CN=${genotype.cn}`
    }
  }
  const position = ref ? `${pos} ${ref}>${alt}` : `${pos}-${end}`
  return `a${inheritance} ${consequence} ${chrom}:${position}${displayGenomeVersion ? ` (${displayGenomeVersion})` : ''}${variantDetail ? ` (${variantDetail})` : ''}`
}

const getPopAf = population => (variant) => {
  const populationData = (variant.populations || {})[population]
  return (populationData || {}).af
}

const getVariantGene = (variant, tagsByGuid, notesByGuid, genesById) => {
  const { geneId } = getVariantMainTranscript(variant)
  return genesById[geneId]?.geneSymbol || geneId
}

export const VARIANT_EXPORT_DATA = [
  { header: 'chrom' },
  { header: 'pos' },
  { header: 'ref' },
  { header: 'alt' },
  { header: 'gene', getVal: getVariantGene },
  { header: 'worst_consequence', getVal: variant => getVariantMainTranscript(variant).majorConsequence },
  { header: 'callset_freq', getVal: variant => getPopAf('callset')(variant) || getPopAf('seqr')(variant) },
  { header: 'exac_freq', getVal: getPopAf('exac') },
  { header: 'gnomad_genomes_freq', getVal: getPopAf('gnomad_genomes') },
  { header: 'gnomad_exomes_freq', getVal: getPopAf('gnomad_exomes') },
  { header: 'topmed_freq', getVal: getPopAf('topmed') },
  { header: 'cadd', getVal: variant => (variant.predictions || {}).cadd },
  { header: 'revel', getVal: variant => (variant.predictions || {}).revel },
  { header: 'eigen', getVal: variant => (variant.predictions || {}).eigen },
  { header: 'splice_ai', getVal: variant => (variant.predictions || {}).splice_ai },
  { header: 'polyphen', getVal: variant => (POLYPHEN_MAP[(variant.predictions || {}).polyphen] || {}).value || (variant.predictions || {}).polyphen },
  { header: 'sift', getVal: variant => (INDICATOR_MAP[(variant.predictions || {}).sift] || {}).value || (variant.predictions || {}).sift },
  { header: 'muttaster', getVal: variant => (MUTTASTER_MAP[(variant.predictions || {}).mut_taster] || {}).value },
  { header: 'fathmm', getVal: variant => (INDICATOR_MAP[(variant.predictions || {}).fathmm] || {}).value || (variant.predictions || {}).fathmm },
  { header: 'rsid', getVal: variant => variant.rsid },
  { header: 'hgvsc', getVal: variant => getVariantMainTranscript(variant).hgvsc },
  { header: 'hgvsp', getVal: variant => getVariantMainTranscript(variant).hgvsp },
  { header: 'clinvar_clinical_significance', getVal: variant => (variant.clinvar || {}).clinicalSignificance || (variant.clinvar || {}).pathogenicity },
  { header: 'clinvar_gold_stars', getVal: variant => (variant.clinvar || {}).goldStars },
  { header: 'project' },
  { header: 'family' },
  { header: 'tags', getVal: (variant, tagsByGuid) => variant.tagGuids.map(tagGuid => tagsByGuid[tagGuid].name).join('|') },
  { header: 'classification', getVal: variant => (variant.acmgClassification ? `${variant.acmgClassification.score}, ${variant.acmgClassification.classify}, ${variant.acmgClassification.criteria}` : '') },
  {
    header: 'notes',
    getVal: (variant, tagsByGuid, notesByGuid) => variant.noteGuids.map((noteGuid) => {
      const note = notesByGuid[noteGuid]
      return `${note.createdBy}: ${note.note.replace(/\n/g, ' ')}`
    }).join('|'),
  },
]

export const ALL_INHERITANCE_FILTER = 'all'
export const RECESSIVE_FILTER = 'recessive'
export const HOM_RECESSIVE_FILTER = 'homozygous_recessive'
export const X_LINKED_RECESSIVE_FILTER = 'x_linked_recessive'
export const COMPOUND_HET_FILTER = 'compound_het'
export const DE_NOVO_FILTER = 'de_novo'
export const ANY_AFFECTED = 'any_affected'

export const INHERITANCE_FILTER_OPTIONS = [
  { value: ALL_INHERITANCE_FILTER, text: 'All' },
  {
    value: RECESSIVE_FILTER,
    text: 'Recessive',
    detail: 'This method identifies genes with any evidence of recessive variation. It is the union of all variants returned by the homozygous recessive, x-linked recessive, and compound heterozygous methods.',
  },
  {
    value: HOM_RECESSIVE_FILTER,
    color: 'transparent', // Adds an empty label so option is indented
    text: 'Homozygous Recessive',
    detail: 'Finds variants where all affected individuals are Alt / Alt and each of their parents Heterozygous.',
  },
  {
    value: X_LINKED_RECESSIVE_FILTER,
    color: 'transparent', // Adds an empty label so option is indented
    text: 'X-Linked Recessive',
    detail: "Recessive inheritance on the X Chromosome. This is similar to the homozygous recessive search, but a proband's father must be homozygous reference. (This is how hemizygous genotypes are called by current variant calling methods.)",
  },
  {
    value: COMPOUND_HET_FILTER,
    color: 'transparent', // Adds an empty label so option is indented
    text: 'Compound Heterozygous',
    detail: 'Affected individual(s) have two heterozygous mutations in the same gene on opposite haplotypes. Unaffected individuals cannot have the same combination of alleles as affected individuals, or be homozygous alternate for any of the variants. If parents are not present, this method only searches for pairs of heterozygous variants; they may not be on different haplotypes.',
  },
  {
    value: DE_NOVO_FILTER,
    text: 'De Novo/ Dominant',
    detail: 'Finds variants where all affected individuals have at least one alternate allele and all unaffected are homozygous reference.',
  },
  {
    value: ANY_AFFECTED,
    text: 'Any Affected',
    detail: 'Finds variants where at least one affected individual has at least one alternate allele.',
  },
]

const VARIANT_ICON_COLORS = {
  red: '#eaa8a8',
  amber: '#f5d55c',
  green: '#21a926',
}

export const PANEL_APP_CONFIDENCE_DESCRIPTION = {
  0: 'No Panel App confidence level',
  1: 'Red, lowest level of confidence; 1 of the 4 sources or from other sources.',
  2: 'Amber, intermediate; a gene from 2 sources',
  3: 'Green, highest level of confidence; a gene from 3 or 4 sources.',
  4: 'Green, highest level of confidence; a gene from 3 or 4 sources.',
}

export const PANEL_APP_CONFIDENCE_LEVELS = {
  0: 'none',
  1: 'red',
  2: 'amber',
  3: 'green',
  4: 'green',
}

export const PANEL_APP_CONFIDENCE_LEVEL_COLORS = Object.entries(PANEL_APP_CONFIDENCE_LEVELS).reduce(
  (acc, [confidence, color]) => ({ ...acc, [confidence]: VARIANT_ICON_COLORS[color] }), {},
)

export const AD_MOI = 'AD'
export const AR_MOI = 'AR'
export const XD_MOI = 'XD'
export const XR_MOI = 'XR'
export const OTHER_MOI = 'other'

export const PANEL_APP_MOI_OPTIONS = [{
  text: 'Autosomal Dominant',
  value: AD_MOI,
},
{
  text: 'Autosomal Recessive',
  value: AR_MOI,
},
{
  text: 'X-Linked Dominant',
  value: XD_MOI,
},
{
  text: 'X-Linked Recessive',
  value: XR_MOI,
},
{
  text: 'Other Modes of Inheritance',
  value: OTHER_MOI,
}]

// Users

export const USER_NAME_FIELDS = [
  {
    name: 'firstName',
    label: 'First Name',
    width: 8,
    inline: true,
  },
  {
    name: 'lastName',
    label: 'Last Name',
    width: 8,
    inline: true,
  },
]

// ACMG Classification
export const ACMG_RULE_SPECIFICATION_CATEGORY_CRITERIA = [
  {
    rules:
    [
      { key: 'rs_hcm_dcm_01', value: 'HCM/DCM: >= 0.1%' },
      { key: 'rs_noonan_005', value: 'Noonan: >= 0.05%' },
      { key: 'rs_default_06', value: 'Default: >= 0.6%' },
      { key: 'rs_autosomal_recessive_05', value: 'HL (Autosomal recessive): >= 0.5%' },
      { key: 'hl_autosomal_dominan_01', value: 'HL (Autosomal dominant): >= 0.1%' },
    ],
    name: 'BA1',
  },
  {
    rules:
    [
      { key: 'rs_hcm_dcm_02', value: 'HCM/DCM: >= 0.2%' },
      { key: 'rs_noonan_0025', value: 'Noonan: >= 0.025%' },
      { key: 'rs_default_03', value: 'Default: >= 0.3%' },
      { key: 'rs_autosomal_recessive_03', value: 'HL (Autosomal recessive): >= 0.3%' },
      { key: 'hl_autosomal_dominan_02', value: 'HL (Autosomal dominant): >= 0.02%' },
    ],
    name: 'BS1',
  },
  {
    rules:
    [
      { key: 'rs_autosomal_recessive_0703', value: 'HL (Autosomal recessive): 0.07-0.3%' },
    ],
    name: 'BS1_P',
  },
  {
    rules:
    [
      { key: 'rs_autosomal_recessive_007', value: 'HL (Autosomal recessive): <= 0.007%' },
      { key: 'hl_autosomal_dominan_002', value: 'HL (Autosomal dominant): <= 0.002%' },
    ],
    name: 'PM2_P',
  },
]

export const ACMG_RULE_SPECIFICATION_PROBAND = [
  [['Noonan', '#'], ['Strong', '5'], ['Moderate', '3'], ['Supporting', '1']],
  [['Cardio', '#'], ['Strong', '15'], ['Moderate', '6'], ['Supporting', '2']],
]

export const ACMG_RULE_SPECIFICATION_IN_TRANS = [
  [
    { value: 'Increase to PM3_Strong if observed in trans' },
    {
      isList: true,
      listItems: [
        { key: 'rs_2x_and_1_variant_path', value: '2x and >= 1 variant in PATH' },
        { key: 'rs_3x_other_variants_lp', value: '3x if other variants are LP' },
      ],
    },
  ],
  [
    { value: 'Increase to VeryStrong if observed in trans' },
    {
      isList: true,
      listItems: [
        { key: 'rs_4x_and_2_variant_path', value: '4x and >= 2 variant in PATH (can be same variant)' },
        { key: 'rs_4x_lpp_different', value: '4x if LP/P variants are all different' },
      ],
    },
  ],
]

export const ACMG_RULE_SPECIFICATION_LEVELS_TABLE = [
  ['', 'Supporting', 'Moderate', 'Strong'],
  ['Likelihood', '4:1', '16:1', '32:1'],
  ['LOD Score', '0.6', '1.2', '1.5'],
  ['Autosomal dominant threshold', '2 affected segregations', '4 affected segregations', '5 affected segregations<'],
  ['Autosomal recessive threshold', 'See Table 2', 'See Table 2', 'See Table 2'],
]

export const ACMG_RULE_SPECIFICATION_GENERAL_RECOMMENDATIONS = [
  [0, 0, 0.12, 0.25, 0.37, 0.5, 0.62, 0.75, 0.87, 1, 1.2, 1.25],
  [1, 0.6, 0.73, 0.85, 0.98, 1.1, 1.23, 1.35, 1.48, 1.6, 1.73, 1.85],
  [2, 1.2, 1.33, 1.45, 1.58, 1.7, 1.83, 1.95, 2.08, 2.2, 2.33, 2.45],
  [3, 1.81, 1.83, 2.06, 2.18, 2.31, 2.43, 2.56, 2.68, 2.81, 2.93, 3.06],
  [4, 2.41, 2.53, 2.66, 2.78, 2.91, 3.03, 3.16, 3.28, 3.41, 3.53, 3.06],
  [5, 3.01, 3.14, 3.26, 3.39, 3.51, 3.63, 3.76, 3.88, 4.01, 4.13, 4.26],
  [6, 3.61, 3.74, 3.86, 3.99, 4.11, 4.24, 4.36, 4.49, 4.61, 4.74, 4.86],
  [7, 4.21, 4.34, 4.46, 4.59, 4.71, 4.84, 4.96, 5.09, 5.21, 5.34, 5.46],
  [8, 4.82, 4.94, 5.07, 5.19, 5.32, 5.44, 5.57, 5.69, 5.82, 5.94, 6.07],
  [9, 5.42, 5.54, 5.67, 5.79, 5.92, 6.04, 6.17, 6.29, 6.42, 6.54, 6.67],
  [10, 6.02, 6.15, 6.27, 6.4, 6.52, 6.65, 6.77, 6.9, 7.02, 7.15, 7.27],
]

export const ACMG_RULE_SPECIFICATION_PM3 = [
  ['Pathogenic/Likely pathogenic', '1.0', '0.5'],
  ['Homozygous occurrence (Max points from homozygotes 1)', '0.5', 'N/A'],
  ['Homozygous occurrence due to consanguinity, rare uncertain significance (confirmed in trans) (Max point 0.5)', '0.25', '0'],
]

export const ACMG_RULE_SPECIFICATION_DISEASE_BASED_CRITERIA = [
  { key: 'cardiomyopathy', value: 'Cardiomyopathy', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN002' },
  { key: 'rasopathy', value: 'RASopathy', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN004' },
  { key: 'hearing-loss', value: 'Hearing Loss', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN005' },
  { key: 'rett-angelman-disorders', value: 'Rett and Angelman-like Disorders', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN016' },
  { key: 'mitochondrial-disease-mitochondrial', value: 'Mitochondrial Disease Mitochondrial', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN015' },
  { key: 'mitochondrial-disease-nuclear', value: 'Mitochondrial Disease Nuclear', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN014' },
  { key: 'hypercholesterolemia', value: 'Hypercholesterolemia', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN013' },
  { key: 'hyperthermia-susceptibility', value: 'Hyperthermia Susceptibility', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN012' },
  { key: 'platelet-discorders', value: 'Platelet Disorders', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN011' },
  { key: 'lysosmal-storage-disorders', value: 'Lysosomal Storage Disorders', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN010' },
  { key: 'pten', value: 'PTEN', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN003' },
  { key: 'myeloid-malignancy', value: 'Myeloid Malignancy', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN008' },
  { key: 'cdh1', value: 'CDH1', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN008' },
  { key: 'tps3', value: 'TPS3', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN009' },
  { key: 'pah', value: 'PAH', href: 'https://cspec.genome.network/cspec/ui/svi/svi/GN006' },
]

export const ACMG_RULE_SPECIFICATION_COMP_HET = [
  [
    { value: 'Supporting (PM3_Supporting) (total 0.5 points)' },
    { value: '1 observation with LP/P but phase unknown or 2 VUS co-occurrences (exception: large genes)' },
    { value: '1 with ADO rules out' },
    { value: 'N/A' },
  ],
  [
    { value: 'Moderate (PM3) (total 1.0 points)' },
    { value: '1 comp het  with LP/P 2 observations with different LP/P but phase unknown' },
    { value: '2 difference families and use of exome data to rule out consanguinity' },
    {
      description: 'A combination of the following adding to 1 point',
      isList: true,
      listItems: [
        { key: 'rs_observations_with_lpp', value: 'Observations with LP/P but phase unknown' },
        { key: 'rs_compund_rare_vus', value: 'Compound het with rare VUS' },
        { key: 'rs_hom_ado_rules_out', value: 'Hom w/ ADO rules out' },
      ],
    },
  ],
  [
    { value: 'Strong (PM3_Strong) (total 2.0 points)' },
    { value: '2 comp het' },
    { value: 'N/A' },
    {
      desription: 'A combination of the following adding to 2 points',
      isList: true,
      listItems: [
        { key: 'rs_comp_lpp', value: 'Comp het with LP/P' },
        { key: 'rs_hom_ado_rules_out_2', value: 'Hom w/ ADO rules out' },
        { key: 'rs_observations_lpp_phase_unknown', value: 'Observations with different LP/P but phase unknown' },
        { key: 'rs_compund_rare_vus_2', value: 'Compund het with rare VUS' },
      ],
    },
  ],
  [
    { value: 'Very Strong (PM3_VeryStrong) (total 4.0 points)' },
    { value: '4 comp het' },
    { value: 'N/A' },
    {
      description: 'A combination of the following adding to 4 points',
      isList: true,
      listItems: [
        { key: 'rs_comp_lpp_2', value: 'Comp hets with LP/P' },
        { key: 'rs_different_observations_lpp_phase_unknown', value: 'Different observations with LP/P but phase unknown' },
        { key: 'rs_compund_rare_vus_3', value: 'Compound het with rare VUS' },
        { key: 'rs_hom_ado_rules_out_3', value: 'How w/ ADO ruled out' },
      ],
    },
  ],
]

export const VARIANT_METADATA_COLUMNS = [
  { name: 'genetic_findings_id' },
  { name: 'variant_reference_assembly' },
  { name: 'chrom' },
  { name: 'pos' },
  { name: 'chrom_end' },
  { name: 'pos_end' },
  { name: 'ref' },
  { name: 'alt' },
  { name: 'gene_of_interest', secondaryExportColumn: 'gene_id' },
  { name: 'seqr_chosen_consequence' },
  { name: 'transcript' },
  { name: 'hgvsc' },
  { name: 'hgvsp' },
  { name: 'zygosity' },
  { name: 'copy_number' },
  { name: 'sv_name' },
  { name: 'validated_name' },
  { name: 'sv_type', format: ({ sv_type }) => SVTYPE_LOOKUP[sv_type] || sv_type }, // eslint-disable-line camelcase
  { name: 'variant_inheritance' },
  { name: 'gene_known_for_phenotype' },
  { name: 'phenotype_contribution' },
  { name: 'partial_contribution_explained' },
  { name: 'notes' },
  { name: 'ClinGen_allele_ID' },
]

export const BASE_FAMILY_METADATA_COLUMNS = [
  { name: 'pmid_id' },
  { name: 'condition_id' },
  { name: 'known_condition_name' },
  { name: 'condition_inheritance', secondaryExportColumn: 'disorders' },
  { name: 'phenotype_description', style: { minWidth: '200px' } },
  { name: 'analysis_groups' },
  {
    name: 'analysisStatus',
    content: 'analysis_status',
    format: ({ analysisStatus }) => FAMILY_ANALYSIS_STATUS_LOOKUP[analysisStatus]?.name,
  },
  { name: 'solve_status' },
  { name: 'data_type' },
  { name: 'date_data_generation', secondaryExportColumn: 'filter_flags' },
  { name: 'consanguinity' },
]

// RNAseq sample tissue type mapping
export const TISSUE_DISPLAY = {
  WB: 'Whole Blood',
  F: 'Fibroblast',
  M: 'Muscle',
  L: 'Lymphocyte',
  A: 'Airway Cultured Epithelium',
  B: 'Brain',
}

export const RNASEQ_JUNCTION_PADDING = 200

export const FAQ_PATH = '/faq'
export const MATCHMAKER_PATH = '/matchmaker'
export const PRIVACY_PATH = '/privacy_policy'
export const TOS_PATH = '/terms_of_service'
export const FEATURE_UPDATES_PATH = '/feature_updates'
export const PUBLIC_PAGES = [MATCHMAKER_PATH, FAQ_PATH, PRIVACY_PATH, TOS_PATH, FEATURE_UPDATES_PATH]

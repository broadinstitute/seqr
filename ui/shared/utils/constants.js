import React from 'react'
import { Form } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'
import flatten from 'lodash/flatten'

import { validators } from '../components/form/ReduxFormWrapper'
import {
  BooleanCheckbox,
  RadioGroup,
  Dropdown,
  Select,
  InlineToggle,
  Pagination,
  BaseSemanticInput,
} from '../components/form/Inputs'
import BaseFieldView from '../components/panel/view-fields/BaseFieldView'
import OptionFieldView from '../components/panel/view-fields/OptionFieldView'
import ListFieldView from '../components/panel/view-fields/ListFieldView'
import SingleFieldView from '../components/panel/view-fields/SingleFieldView'
import TagFieldView from '../components/panel/view-fields/TagFieldView'

import { stripMarkdown } from './stringUtils'
import { ColoredIcon } from '../components/StyledComponents'

export const ANVIL_URL = 'https://anvil.terra.bio'

export const GENOME_VERSION_37 = '37'
export const GENOME_VERSION_38 = '38'
export const GENOME_VERSION_OPTIONS = [
  { value: GENOME_VERSION_37, text: 'GRCh37' },
  { value: GENOME_VERSION_38, text: 'GRCh38' },
]
export const GENOME_VERSION_LOOKUP = GENOME_VERSION_OPTIONS.reduce((acc, { value, text }) =>
  ({ ...acc, [value]: text }), {})
export const GENOME_VERSION_FIELD = {
  name: 'genomeVersion', label: 'Genome Version', component: RadioGroup, options: GENOME_VERSION_OPTIONS,
}

export const GENOME_VERSION_DISPLAY_LOOKUP = {
  GRCh37: 'hg19',
  GRCh38: 'hg38',
}

// PROJECT FIELDS

export const FILE_FIELD_NAME = 'uploadedFile'

export const PROJECT_DESC_FIELD = { name: 'description', label: 'Project Description', placeholder: 'Description' }

export const EDITABLE_PROJECT_FIELDS = [
  { name: 'name', label: 'Project Name', placeholder: 'Name', validate: validators.required, autoFocus: true },
  PROJECT_DESC_FIELD,
]

export const PROJECT_FIELDS = [
  ...EDITABLE_PROJECT_FIELDS,
  GENOME_VERSION_FIELD,
]

export const FILE_FORMATS = [
  { title: 'Excel', ext: 'xls' },
  {
    title: 'Text',
    ext: 'tsv',
    formatLinks: [
      { href: 'https://en.wikipedia.org/wiki/Tab-separated_values', linkExt: 'tsv' },
      { href: 'https://en.wikipedia.org/wiki/Comma-separated_values', linkExt: 'csv' },
    ] },
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

export const DATASET_TYPE_VARIANT_CALLS = 'VARIANTS'
export const DATASET_TYPE_SV_CALLS = 'SV'

export const SAMPLE_TYPE_EXOME = 'WES'
export const SAMPLE_TYPE_GENOME = 'WGS'
export const SAMPLE_TYPE_RNA = 'RNA'

export const SAMPLE_TYPE_OPTIONS = [
  { value: SAMPLE_TYPE_EXOME, text: 'Exome' },
  { value: SAMPLE_TYPE_GENOME, text: 'Genome' },
  { value: SAMPLE_TYPE_RNA, text: 'RNA-seq' },
]

export const SAMPLE_TYPE_LOOKUP = SAMPLE_TYPE_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt },
  }), {},
)

// ANALYSIS STATUS

export const FAMILY_STATUS_SOLVED = 'S'
export const FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE = 'S_kgfp'
export const FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'S_kgdp'
export const FAMILY_STATUS_SOLVED_NOVEL_GENE = 'S_ng'
export const FAMILY_STATUS_EXTERNAL_SOLVE = 'ES'
export const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE = 'Sc_kgfp'
export const FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE = 'Sc_kgdp'
export const FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE = 'Sc_ng'
export const FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES = 'Rcpc'
export const FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE = 'Rncc'
export const FAMILY_STATUS_CLOSED = 'C'
export const FAMILY_STATUS_ANALYSIS_IN_PROGRESS = 'I'
const FAMILY_STATUS_WAITING_FOR_DATA = 'Q'

export const FAMILY_ANALYSIS_STATUS_OPTIONS = [
  { value: FAMILY_STATUS_SOLVED, color: '#4CAF50', name: 'Solved' },
  { value: FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE, color: '#4CAF50', name: 'Solved - known gene for phenotype' },
  { value: FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE, color: '#4CAF50', name: 'Solved - gene linked to different phenotype' },
  { value: FAMILY_STATUS_SOLVED_NOVEL_GENE, color: '#4CAF50', name: 'Solved - novel gene' },
  { value: FAMILY_STATUS_EXTERNAL_SOLVE, color: '#146917', name: 'External Solve' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE, color: '#CDDC39', name: 'Strong candidate - known gene for phenotype' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE, color: '#CDDC39', name: 'Strong candidate - gene linked to different phenotype' },
  { value: FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE, color: '#CDDC39', name: 'Strong candidate - novel gene' },
  { value: FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES, color: '#CDDC39', name: 'Reviewed, currently pursuing candidates' },
  { value: FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE, color: '#EF5350', name: 'Reviewed, no clear candidate' },
  { value: FAMILY_STATUS_CLOSED, color: '#9c0502', name: 'Closed, no longer under analysis' },
  { value: FAMILY_STATUS_ANALYSIS_IN_PROGRESS, color: '#4682B4', name: 'Analysis in Progress' },
  { value: FAMILY_STATUS_WAITING_FOR_DATA, color: '#FFC107', name: 'Waiting for data' },
]

export const FAMILY_ANALYSIS_STATUS_LOOKUP = FAMILY_ANALYSIS_STATUS_OPTIONS.reduce((acc, tag) => {
  return { [tag.value]: tag, ...acc }
}, {})

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

export const FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP = FAMILY_SUCCESS_STORY_TYPE_OPTIONS.reduce((acc, tag) => {
  return { [tag.value]: tag, ...acc }
}, {})

export const successStoryTypeDisplay = tag =>
  <span>
    <ColoredIcon name="stop" color={FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP[tag].color} />
    {FAMILY_SUCCESS_STORY_TYPE_OPTIONS_LOOKUP[tag].name}
  </span>

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
export const FAMILY_FIELD_ANALYSIS_SUMMARY = 'analysisSummary'
export const FAMILY_FIELD_MME_NOTES = 'mmeNotes'
export const FAMILY_FIELD_INTERNAL_NOTES = 'caseReviewNotes'
export const FAMILY_FIELD_INTERNAL_SUMMARY = 'caseReviewSummary'
export const FAMILY_FIELD_FIRST_SAMPLE = 'firstSample'
export const FAMILY_FIELD_CODED_PHENOTYPE = 'codedPhenotype'
export const FAMILY_FIELD_OMIM_NUMBER = 'postDiscoveryOmimNumber'
export const FAMILY_FIELD_PMIDS = 'pubmedIds'
export const FAMILY_FIELD_PEDIGREE = 'pedigreeImage'
export const FAMILY_FIELD_CREATED_DATE = 'createdDate'

export const FAMILY_FIELD_RENDER_LOOKUP = {
  [FAMILY_FIELD_DESCRIPTION]: { name: 'Family Description' },
  [FAMILY_FIELD_ANALYSIS_STATUS]: { name: 'Analysis Status', component: OptionFieldView },
  [FAMILY_FIELD_ASSIGNED_ANALYST]: {
    name: 'Assigned Analyst',
    component: BaseFieldView,
    submitArgs: { familyField: 'assigned_analyst' },
  },
  [FAMILY_FIELD_ANALYSED_BY]: {
    name: 'Analysed By',
    component: BaseFieldView,
    submitArgs: { familyField: 'analysed_by' },
  },
  [FAMILY_FIELD_SUCCESS_STORY_TYPE]: {
    name: 'Success Story Type',
    component: TagFieldView,
    internal: true,
  },
  [FAMILY_FIELD_SUCCESS_STORY]: { name: 'Success Story', internal: true },
  [FAMILY_FIELD_FIRST_SAMPLE]: { name: 'Data Loaded?', component: BaseFieldView },
  [FAMILY_FIELD_ANALYSIS_NOTES]: { name: 'Notes' },
  [FAMILY_FIELD_ANALYSIS_SUMMARY]: { name: 'Analysis Summary' },
  [FAMILY_FIELD_MME_NOTES]: { name: 'Matchmaker Notes' },
  [FAMILY_FIELD_CODED_PHENOTYPE]: { name: 'Coded Phenotype', component: SingleFieldView },
  [FAMILY_FIELD_OMIM_NUMBER]: { name: 'Post-discovery OMIM #', component: SingleFieldView },
  [FAMILY_FIELD_PMIDS]: { name: 'Publications on this discovery', component: ListFieldView },
  [FAMILY_FIELD_INTERNAL_NOTES]: {
    name: 'Internal Notes',
    internal: true,
    submitArgs: { familyField: 'case_review_notes' },
  },
  [FAMILY_FIELD_INTERNAL_SUMMARY]: {
    name: 'Internal Summary',
    internal: true,
    submitArgs: { familyField: 'case_review_summary' },
  },
}

export const FAMILY_DETAIL_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_STATUS, canEdit: true },
  { id: FAMILY_FIELD_ASSIGNED_ANALYST, canEdit: true, collaboratorEdit: true },
  { id: FAMILY_FIELD_ANALYSED_BY, canEdit: true, collaboratorEdit: true },
  { id: FAMILY_FIELD_SUCCESS_STORY_TYPE, canEdit: true },
  { id: FAMILY_FIELD_SUCCESS_STORY, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_NOTES, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY, canEdit: true },
  { id: FAMILY_FIELD_MME_NOTES, canEdit: true },
  { id: FAMILY_FIELD_CODED_PHENOTYPE, canEdit: true },
  { id: FAMILY_FIELD_OMIM_NUMBER, canEdit: true },
  { id: FAMILY_FIELD_PMIDS, canEdit: true },
]

// INDIVIDUAL FIELDS

export const SEX_OPTIONS = [
  { value: 'M', text: 'Male' },
  { value: 'F', text: 'Female' },
  { value: 'U', text: '?' },
]

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

export const INDIVIDUAL_FIELD_ID = 'individualId'
export const INDIVIDUAL_FIELD_PATERNAL_ID = 'paternalId'
export const INDIVIDUAL_FIELD_MATERNAL_ID = 'maternalId'
export const INDIVIDUAL_FIELD_SEX = 'sex'
export const INDIVIDUAL_FIELD_AFFECTED = 'affected'
export const INDIVIDUAL_FIELD_NOTES = 'notes'
export const INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP = 'probandRelationship'

export const INDIVIDUAL_FIELD_CONFIGS = {
  [FAMILY_FIELD_ID]: { label: 'Family ID' },
  [INDIVIDUAL_FIELD_ID]: { label: 'Individual ID' },
  [INDIVIDUAL_FIELD_PATERNAL_ID]: { label: 'Paternal ID', description: 'Individual ID of the father' },
  [INDIVIDUAL_FIELD_MATERNAL_ID]: { label: 'Maternal ID', description: 'Individual ID of the mother' },
  [INDIVIDUAL_FIELD_SEX]: {
    label: 'Sex',
    format: sex => SEX_LOOKUP[sex],
    width: 3,
    description: 'Male or Female, leave blank if unknown',
    formFieldProps: { component: RadioGroup, options: SEX_OPTIONS },
  },
  [INDIVIDUAL_FIELD_AFFECTED]: {
    label: 'Affected Status',
    format: affected => AFFECTED_LOOKUP[affected],
    width: 4,
    description: 'Affected or Unaffected, leave blank if unknown',
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
}


export const INDIVIDUAL_HPO_EXPORT_DATA = [
  {
    header: 'HPO Terms (present)',
    field: 'features',
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

export const INDIVIDUAL_BULK_UPDATE_EXPORT_DATA = [
  ...INDIVIDUAL_CORE_EXPORT_DATA, exportConfigForField(INDIVIDUAL_FIELD_CONFIGS)(INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP),
]

export const INDIVIDUAL_EXPORT_DATA = [].concat(
  INDIVIDUAL_ID_EXPORT_DATA, INDIVIDUAL_CORE_EXPORT_DATA, [INDIVIDUAL_HAS_DATA_EXPORT_CONFIG], INDIVIDUAL_HPO_EXPORT_DATA,
)

export const familyVariantSamples = (family, individualsByGuid, samplesByGuid) => {
  const sampleGuids = [...(family.individualGuids || []).map(individualGuid => individualsByGuid[individualGuid]).reduce(
    (acc, individual) => new Set([...acc, ...(individual.sampleGuids || [])]), new Set(),
  )]
  const loadedSamples = sampleGuids.map(sampleGuid => samplesByGuid[sampleGuid])
  return orderBy(loadedSamples, [s => s.loadedDate], 'asc')
}

// CLINVAR

export const CLINSIG_SEVERITY = {
  // clinvar
  pathogenic: 1,
  'risk factor': 0,
  risk_factor: 0,
  'likely pathogenic': 1,
  'pathogenic/likely_pathogenic': 1,
  likely_pathogenic: 1,
  benign: -1,
  'likely benign': -1,
  'benign/likely_benign': -1,
  likely_benign: -1,
  protective: -1,
  // hgmd
  DM: 1,
  'DM?': 0,
  FPV: 0,
  FP: 0,
  DFP: 0,
  DP: 0,
}


// LOCUS LISTS

export const LOCUS_LIST_NAME_FIELD = 'name'
export const LOCUS_LIST_NUM_ENTRIES_FIELD = 'numEntries'
export const LOCUS_LIST_DESCRIPTION_FIELD = 'description'
export const LOCUS_LIST_IS_PUBLIC_FIELD_NAME = 'isPublic'
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
    width: 9,
    isEditable: true,
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
  {
    description: 'A large deletion',
    text: 'Deletion',
    value: 'DEL',
    group: VEP_GROUP_SV,
  },
  {
    description: 'A large duplication',
    text: 'Duplication',
    value: 'DUP',
    group: VEP_GROUP_SV,
  },
  {
    description: 'A sequence variant where at least one base of the terminator codon (stop) is changed, resulting in an elongated transcript',
    text: 'Stop lost',
    value: 'stop_lost',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001578',
  },
  {
    description: 'A codon variant that changes at least one base of the first codon of a transcript',
    text: 'Initiator codon',
    value: 'initiator_codon_variant',
    group: VEP_GROUP_MISSENSE,
    so: 'SO:0001582',
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
    description: 'A feature amplification of a region containing a transcript',
    text: 'Transcript amplification',
    value: 'transcript_amplification',
    so: 'SO:0001889',
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
    description: 'A sequence variant in which a change has occurred within the region of the splice site, either within 1-3 bases of the exon or 3-8 bases of the intron',
    text: 'Splice region',
    value: 'splice_region_variant',
    group: VEP_GROUP_EXTENDED_SPLICE_SITE,
    so: 'SO:0001630',
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
  //2 kinds of 'non_coding_transcript_exon_variant' text due to value change in Ensembl v77
  {
    description: 'A sequence variant that changes non-coding exon sequence',
    text: 'Non-coding exon variant',
    value: 'non_coding_exon_variant',
    so: 'SO:0001792',
  },
  {
    description: 'A sequence variant that changes non-coding exon sequence',
    text: 'Non-coding transcript exon variant',
    value: 'non_coding_transcript_exon_variant',
    so: 'SO:0001792',
  },
  // 2 kinds of 'nc_transcript_variant' text due to value change in Ensembl v77
  {
    description: 'A transcript variant of a non coding RNA',
    text: 'nc transcript variant',
    value: 'nc_transcript_variant',
    so: 'SO:0001619',
  },
  {
    description: 'A transcript variant of a non coding RNA',
    text: 'Non-coding transcript variant',
    value: 'non_coding_transcript_variant',
    so: 'SO:0001619',
  },
  {
    description: 'A feature ablation whereby the deleted region includes a transcription factor binding site',
    text: 'TFBS ablation',
    value: 'TFBS_ablation',
    so: 'SO:0001895',
  },
  {
    description: 'A feature amplification of a region containing a transcription factor binding site',
    text: 'TFBS amplification',
    value: 'TFBS_amplification',
    so: 'SO:0001892',
  },
  {
    description: 'In regulatory region annotated by Ensembl',
    text: 'TF binding site variant',
    value: 'TF_binding_site_variant',
    so: 'SO:0001782',
  },
  {
    description: 'A sequence variant located within a regulatory region',
    text: 'Regulatory region variant',
    value: 'regulatory_region_variant',
    so: 'SO:0001566',
  },
  {
    description: 'A feature ablation whereby the deleted region includes a regulatory region',
    text: 'Regulatory region ablation',
    value: 'regulatory_region_ablation',
    so: 'SO:0001894',
  },
  {
    description: 'A feature amplification of a region containing a regulatory region',
    text: 'Regulatory region amplification',
    value: 'regulatory_region_amplification',
    so: 'SO:0001891',
  },
  {
    description: 'A sequence variant that causes the extension of a genomic feature, with regard to the reference sequence',
    text: 'Feature elongation',
    value: 'feature_elongation',
    so: 'SO:0001907',
  },
  {
    description: 'A sequence variant that causes the reduction of a genomic feature, with regard to the reference sequence',
    text: 'Feature truncation',
    value: 'feature_truncation',
    so: 'SO:0001906',
  },
  {
    description: 'A sequence variant located in the intergenic region, between genes',
    text: 'Intergenic variant',
    value: 'intergenic_variant',
    so: 'SO:0001628',
  },
]

export const GROUPED_VEP_CONSEQUENCES = ORDERED_VEP_CONSEQUENCES.reduce((acc, consequence) => {
  const group = consequence.group || VEP_GROUP_OTHER
  acc[group] = [...(acc[group] || []), consequence]
  return acc
}, {})

export const VEP_CONSEQUENCE_ORDER_LOOKUP = ORDERED_VEP_CONSEQUENCES.reduce((acc, consequence, i) =>
  ({ ...acc, [consequence.value]: i }),
{})

export const SHOW_ALL = 'ALL'
export const NOTE_TAG_NAME = 'Has Notes'
export const EXCLUDED_TAG_NAME = 'Excluded'
export const REVIEW_TAG_NAME = 'Review'
export const KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME = 'Known gene for phenotype'
export const DISCOVERY_CATEGORY_NAME = 'CMG Discovery Tags'


export const SORT_BY_FAMILY_GUID = 'FAMILY_GUID'
export const SORT_BY_XPOS = 'XPOS'
const SORT_BY_PATHOGENICITY = 'PATHOGENICITY'
const SORT_BY_IN_OMIM = 'IN_OMIM'
const SORT_BY_PROTEIN_CONSQ = 'PROTEIN_CONSEQUENCE'
const SORT_BY_GNOMAD = 'GNOMAD'
const SORT_BY_EXAC = 'EXAC'
const SORT_BY_1KG = '1KG'
const SORT_BY_CONSTRAINT = 'CONSTRAINT'
const SORT_BY_CADD = 'CADD'
const SORT_BY_REVEL = 'REVEL'
const SORT_BY_SPLICE_AI = 'SPLICE_AI'
const SORT_BY_EIGEN = 'EIGEN'
const SORT_BY_MPC = 'MPC'
const SORT_BY_PRIMATE_AI = 'PRIMATE_AI'
const SORT_BY_TAGGED_DATE = 'TAGGED_DATE'


const clinsigSeverity = (variant, user) => {
  const { clinvar = {}, hgmd = {} } = variant
  const clinvarSignificance = clinvar.clinicalSignificance && clinvar.clinicalSignificance.split('/')[0]
  const hgmdSignificance = user.isAnalyst && hgmd.class
  if (!clinvarSignificance && !hgmdSignificance) return -10
  let clinvarSeverity = 0.1
  if (clinvarSignificance) {
    clinvarSeverity = clinvarSignificance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[clinvarSignificance] + 1 : 0.5
  }
  const hgmdSeverity = hgmdSignificance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[hgmdSignificance] + 0.5 : 0
  return clinvarSeverity + hgmdSeverity
}

export const MISSENSE_THRESHHOLD = 3
export const LOF_THRESHHOLD = 0.35

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

const populationComparator = population => (a, b) =>
  ((a.populations || {})[population] || {}).af - ((b.populations || {})[population] || {}).af

const predictionComparator = prediction => (a, b) =>
  ((b.predictions || {})[prediction] || -1) - ((a.predictions || {})[prediction] || -1)

const getConsequenceRank = ({ transcripts, svType }) => (
  transcripts ? Math.min(...Object.values(transcripts || {}).flat().map(({ majorConsequence }) =>
    VEP_CONSEQUENCE_ORDER_LOOKUP[majorConsequence]).filter(val => val)) : VEP_CONSEQUENCE_ORDER_LOOKUP[svType]
)

const VARIANT_SORT_OPTONS = [
  { value: SORT_BY_FAMILY_GUID, text: 'Family', comparator: (a, b) => a.familyGuids[0].localeCompare(b.familyGuids[0]) },
  { value: SORT_BY_XPOS, text: 'Position', comparator: (a, b) => a.xpos - b.xpos },
  {
    value: SORT_BY_PROTEIN_CONSQ,
    text: 'Protein Consequence',
    comparator: (a, b) => getConsequenceRank(a) - getConsequenceRank(b),
  },
  { value: SORT_BY_GNOMAD, text: 'gnomAD Genomes Frequency', comparator: populationComparator('gnomad_genomes') },
  { value: SORT_BY_EXAC, text: 'ExAC Frequency', comparator: populationComparator('exac') },
  { value: SORT_BY_1KG, text: '1kg  Frequency', comparator: populationComparator('g1k') },
  { value: SORT_BY_CADD, text: 'Cadd', comparator: predictionComparator('cadd') },
  { value: SORT_BY_REVEL, text: 'Revel', comparator: predictionComparator('revel') },
  { value: SORT_BY_EIGEN, text: 'Eigen', comparator: predictionComparator('eigen') },
  { value: SORT_BY_MPC, text: 'MPC', comparator: predictionComparator('mpc') },
  { value: SORT_BY_SPLICE_AI, text: 'Splice AI', comparator: predictionComparator('splice_ai') },
  { value: SORT_BY_PRIMATE_AI, text: 'Primate AI', comparator: predictionComparator('primate_ai') },
  { value: SORT_BY_PATHOGENICITY, text: 'Pathogenicity', comparator: (a, b, geneId, user) => clinsigSeverity(b, user) - clinsigSeverity(a, user) },
  {
    value: SORT_BY_CONSTRAINT,
    text: 'Constraint',
    comparator: (a, b, genesById) =>
      Math.min(...Object.keys(a.transcripts || {}).reduce((acc, geneId) =>
        [...acc, getGeneConstraintSortScore(genesById[geneId] || {})], [])) -
      Math.min(...Object.keys(b.transcripts || {}).reduce((acc, geneId) =>
        [...acc, getGeneConstraintSortScore(genesById[geneId] || {})], [])),
  },
  {
    value: SORT_BY_IN_OMIM,
    text: 'In OMIM',
    comparator: (a, b, genesById) =>
      Object.keys(b.transcripts || {}).reduce(
        (acc, geneId) => (genesById[geneId] ? acc + genesById[geneId].omimPhenotypes.length : acc), 0) -
      Object.keys(a.transcripts || {}).reduce(
        (acc, geneId) => (genesById[geneId] ? acc + genesById[geneId].omimPhenotypes.length : acc), 0),
  },
  {
    value: SORT_BY_TAGGED_DATE,
    text: 'Last Tagged',
    comparator: (a, b, genesById, user, tagsByGuid) =>
      (b.tagGuids.map(
        tagGuid => (tagsByGuid[tagGuid] || {}).lastModifiedDate).sort()[b.tagGuids.length - 1] || '').localeCompare(
        a.tagGuids.map(tagGuid => (tagsByGuid[tagGuid] || {}).lastModifiedDate).sort()[a.tagGuids.length - 1] || '',
      ),
  },
]
const VARIANT_SEARCH_SORT_OPTONS = VARIANT_SORT_OPTONS.slice(1, VARIANT_SORT_OPTONS.length - 1)

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

export const PREDICTION_INDICATOR_MAP = {
  D: { color: 'red', value: 'damaging' },
  A: { color: 'red', value: 'disease causing' },
  T: { color: 'green', value: 'tolerated' },
  N: { color: 'green', value: 'polymorphism' },
  P: { color: 'green', value: 'polymorphism' },
  B: { color: 'green', value: 'benign' },
}

export const POLYPHEN_MAP = {
  D: { value: 'probably damaging' },
  P: { color: 'yellow', value: 'possibly damaging' },
}

export const MUTTASTER_MAP = {
  D: { value: 'disease causing' },
}

export const getVariantMainGeneId = ({ transcripts = {}, mainTranscriptId, selectedMainTranscriptId }) => {
  if (selectedMainTranscriptId || mainTranscriptId) {
    return (Object.entries(transcripts).find(entry =>
      entry[1].some(({ transcriptId }) => transcriptId === (selectedMainTranscriptId || mainTranscriptId)),
    ) || [])[0]
  }
  if (Object.keys(transcripts).length === 1 && Object.values(transcripts)[0] && Object.values(transcripts)[0].length === 0) {
    return Object.keys(transcripts)[0]
  }
  return null
}


export const getVariantMainTranscript = ({ transcripts = {}, mainTranscriptId, selectedMainTranscriptId }) =>
  flatten(Object.values(transcripts)).find(
    ({ transcriptId }) => transcriptId === (selectedMainTranscriptId || mainTranscriptId),
  ) || {}

const getPopAf = population => (variant) => {
  const populationData = (variant.populations || {})[population]
  return (populationData || {}).af
}

export const VARIANT_EXPORT_DATA = [
  { header: 'chrom' },
  { header: 'pos' },
  { header: 'ref' },
  { header: 'alt' },
  { header: 'gene', getVal: variant => getVariantMainTranscript(variant).geneSymbol },
  { header: 'worst_consequence', getVal: variant => getVariantMainTranscript(variant).majorConsequence },
  { header: '1kg_freq', getVal: getPopAf('g1k') },
  { header: 'exac_freq', getVal: getPopAf('exac') },
  { header: 'gnomad_genomes_freq', getVal: getPopAf('gnomad_genomes') },
  { header: 'gnomad_exomes_freq', getVal: getPopAf('gnomad_exomes') },
  { header: 'topmed_freq', getVal: getPopAf('topmed') },
  { header: 'cadd', getVal: variant => (variant.predictions || {}).cadd },
  { header: 'revel', getVal: variant => (variant.predictions || {}).revel },
  { header: 'eigen', getVal: variant => (variant.predictions || {}).eigen },
  { header: 'splice_ai', getVal: variant => (variant.predictions || {}).splice_ai },
  { header: 'polyphen', getVal: variant => (MUTTASTER_MAP[(variant.predictions || {}).polyphen] || PREDICTION_INDICATOR_MAP[(variant.predictions || {}).polyphen] || {}).value },
  { header: 'sift', getVal: variant => (PREDICTION_INDICATOR_MAP[(variant.predictions || {}).sift] || {}).value },
  { header: 'muttaster', getVal: variant => (MUTTASTER_MAP[(variant.predictions || {}).mut_taster] || PREDICTION_INDICATOR_MAP[(variant.predictions || {}).mut_taster] || {}).value },
  { header: 'fathmm', getVal: variant => (PREDICTION_INDICATOR_MAP[(variant.predictions || {}).fathmm] || {}).value },
  { header: 'rsid', getVal: variant => variant.rsid },
  { header: 'hgvsc', getVal: variant => getVariantMainTranscript(variant).hgvsc },
  { header: 'hgvsp', getVal: variant => getVariantMainTranscript(variant).hgvsp },
  { header: 'clinvar_clinical_significance', getVal: variant => (variant.clinvar || {}).clinicalSignificance },
  { header: 'clinvar_gold_stars', getVal: variant => (variant.clinvar || {}).goldStars },
  { header: 'filter', getVal: variant => variant.genotypeFilters },
  { header: 'family', getVal: variant => variant.familyGuids[0].split(/_(.+)/)[1] },
  { header: 'tags', getVal: (variant, tagsByGuid) => (tagsByGuid[variant.variantGuid] || []).map(tag => tag.name).join('|') },
  { header: 'notes', getVal: (variant, tagsByGuid, notesByGuid) => (notesByGuid[variant.variantGuid] || []).map(note => `${note.createdBy}: ${note.note.replace(/\n/g, ' ')}`).join('|') },
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
    detail: 'Finds variants where all affected indivs have at least one alternate allele and all unaffected are homozygous reference.',
  },
  {
    value: ANY_AFFECTED,
    text: 'Any Affected',
    detail: 'Finds variants where at least one affected individual has at least one alternate allele.',
  },
]

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


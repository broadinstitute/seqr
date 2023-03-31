/* eslint-disable no-multi-spaces */

import { stripMarkdown } from 'shared/utils/stringUtils'
import {
  SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_FIELD_ID,
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ASSIGNED_ANALYST,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_CASE_NOTES,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_CREATED_DATE,
  FAMILY_FIELD_CODED_PHENOTYPE,
  FAMILY_FIELD_MONDO_ID,
  FAMILY_FIELD_SAVED_VARIANTS,
  FAMILY_FIELD_NAME_LOOKUP,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
  INDIVIDUAL_FIELD_NOTES,
  INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP,
  ALL_FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_ANALYSIS_STATUS_LOOKUP,
  INDIVIDUAL_FIELD_CONFIGS,
  SHOW_ALL,
  exportConfigForField,
  INDIVIDUAL_EXPORT_DATA,
  INDIVIDUAL_HPO_EXPORT_DATA,
  FAMILY_NOTES_FIELDS,
  SNP_DATA_TYPE,
  FAMILY_ANALYSED_BY_DATA_TYPES,
  MME_TAG_NAME,
  SAMPLE_TYPE_RNA,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
  DATASET_TITLE_LOOKUP,
} from 'shared/utils/constants'

export const CASE_REVIEW_TABLE_NAME = 'Case Review'

const CASE_REVIEW_STATUS_IN_REVIEW = 'I'
const CASE_REVIEW_STATUS_UNCERTAIN = 'U'
const CASE_REVIEW_STATUS_ACCEPTED = 'A'
const CASE_REVIEW_STATUS_NOT_ACCEPTED = 'R'
export const CASE_REVIEW_STATUS_MORE_INFO_NEEDED = 'Q'
const CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS = 'P'
const CASE_REVIEW_STATUS_WAITLIST = 'W'
const CASE_REVIEW_STATUS_NMI_REVIEW = 'N'
const CASE_REVIEW_STATUS_LOST = 'L'
const CASE_REVIEW_STATUS_INACTIVE = 'V'

export const CASE_REVIEW_STATUS_OPTIONS = [
  { value: CASE_REVIEW_STATUS_IN_REVIEW,                   name: 'In Review',             color: '#2196F3' },
  { value: CASE_REVIEW_STATUS_UNCERTAIN,                   name: 'Uncertain',             color: '#fddb28' },
  { value: CASE_REVIEW_STATUS_ACCEPTED,                    name: 'Accepted',              color: '#8BC34A' },
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED,                name: 'Not Accepted',          color: '#4f5cb3' },
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED,            name: 'More Info Needed',      color: '#F44336' },
  { value: CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS, name: 'Pending Results and Records', color: '#996699' },
  { value: CASE_REVIEW_STATUS_NMI_REVIEW,                  name: 'NMI Review',            color: '#3827c1' },
  { value: CASE_REVIEW_STATUS_WAITLIST,                    name: 'Waitlist',              color: '#990099' },
  { value: CASE_REVIEW_STATUS_LOST,                        name: 'Lost To Follow-Up',     color: '#eb7f2f' },
  { value: CASE_REVIEW_STATUS_INACTIVE,                    name: 'Inactive',              color: '#6c6d85' },
]

export const CASE_REVIEW_STATUS_OPT_LOOKUP = CASE_REVIEW_STATUS_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt },
  }), {},
)

export const ONSET_AGE_OPTIONS = [
  { value: 'G', text: 'Congenital onset' },
  { value: 'E', text: 'Embryonal onset' },
  { value: 'F', text: 'Fetal onset' },
  { value: 'N', text: 'Neonatal onset' },
  { value: 'I', text: 'Infantile onset' },
  { value: 'C', text: 'Childhood onset' },
  { value: 'J', text: 'Juvenile onset' },
  { value: 'A', text: 'Adult onset' },
  { value: 'Y', text: 'Young adult onset' },
  { value: 'M', text: 'Middle age onset' },
  { value: 'L', text: 'Late onset' },
]

const ONSET_AGE_LOOKUP = ONSET_AGE_OPTIONS.reduce((acc, option) => ({ ...acc, [option.value]: option.text }), {})

export const INHERITANCE_MODE_OPTIONS = [
  { value: 'S', text: 'Sporadic' },
  { value: 'D', text: 'Autosomal dominant inheritance' },
  { value: 'L', text: 'Sex-limited autosomal dominant' },
  { value: 'A', text: 'Male-limited autosomal dominant' },
  { value: 'C', text: 'Autosomal dominant contiguous gene syndrome' },
  { value: 'R', text: 'Autosomal recessive inheritance' },
  { value: 'G', text: 'Gonosomal inheritance' },
  { value: 'X', text: 'X-linked inheritance' },
  { value: 'Z', text: 'X-linked recessive inheritance' },
  { value: 'Y', text: 'Y-linked inheritance' },
  { value: 'W', text: 'X-linked dominant inheritance' },
  { value: 'F', text: 'Multifactorial inheritance' },
  { value: 'M', text: 'Mitochondrial inheritance' },
]
export const INHERITANCE_MODE_LOOKUP = INHERITANCE_MODE_OPTIONS.reduce(
  (acc, { text, value }) => ({ ...acc, [value]: text }), {},
)

export const AR_FIELDS = {
  arFertilityMeds: 'Fertility medications',
  arIui: 'Intrauterine insemination',
  arIvf: 'In vitro fertilization',
  arIcsi: 'Intra-cytoplasmic sperm injection',
  arSurrogacy: 'Gestational surrogacy',
  arDonoregg: 'Donor egg',
  arDonorsperm: 'Donor sperm',
}

const NULLABLE_BOOL_FIELD = { description: 'true, false, or blank if unknown' }

export const INDIVIDUAL_DETAIL_FIELDS = [
  {
    field: 'probandRelationship',
    header: 'Relationship to Proband',
    isEditable: true,
    isPrivate: true,
    isRequiredInternal: true,
  },
  {
    field: 'age',
    header: 'Age',
    isEditable: true,
    isRequiredInternal: true,
    subFields: [
      { field: 'birthYear', header: 'Birth Year', format: year => year || '' },
      { field: 'deathYear', header: 'Death Year', format: year => year || '' },
    ],
  },
  {
    field: 'onsetAge',
    header: 'Age of Onset',
    isEditable: true,
    description: `One of the following: ${ONSET_AGE_OPTIONS.map(({ text }) => text).join(', ')}`,
    format: val => ONSET_AGE_LOOKUP[val],
  },
  {
    isEditable: true,
    isCollaboratorEditable: true,
    header: 'Individual Notes',
    field: 'notes',
    format: stripMarkdown,
  },
  {
    field: 'consanguinity',
    header: 'Consanguinity',
    isEditable: true,
    ...NULLABLE_BOOL_FIELD,
  },
  {
    field: 'affectedRelatives',
    header: 'Other Affected Relatives',
    isEditable: true,
    ...NULLABLE_BOOL_FIELD,
  },
  {
    field: 'expectedInheritance',
    header: 'Expected Mode of Inheritance',
    isEditable: true,
    description: `comma-separated list of the following: ${INHERITANCE_MODE_OPTIONS.map(({ text }) => text).join(', ')}`,
    format: modes => (modes || []).map(inheritance => INHERITANCE_MODE_LOOKUP[inheritance]).join(', '),
  },
  {
    field: 'ar',
    header: 'Assisted Reproduction',
    isEditable: true,
    subFields: Object.entries(AR_FIELDS).map(([field, header]) => ({ field, header, ...NULLABLE_BOOL_FIELD })),
  },
  {
    field: 'maternalEthnicity',
    header: 'Maternal Ancestry',
    isEditable: true,
    description: 'comma-separated list of ethnicities',
    format: vals => (vals || []).join(', '),
  },
  {
    field: 'paternalEthnicity',
    header: 'Paternal Ancestry',
    isEditable: true,
    description: 'comma-separated list of ethnicities',
    format: vals => (vals || []).join(', '),
  },
  {
    header: 'Imputed Population',
    field: 'population',
    isRequiredInternal: true,
  },
  {
    header: 'Sample QC Flags',
    field: 'filterFlags',
  },
  {
    header: 'Population/Platform Specific Sample QC Flags',
    field: 'popPlatformFilters',
  },
  {
    header: 'SV QC Flags',
    field: 'svFlags',
  },
  {
    field: 'features',
    header: 'Features',
    isEditable: true,
    isRequiredInternal: true,
  },
  {
    field: 'disorders',
    header: 'Pre-discovery OMIM disorders',
    isEditable: true,
    description: 'comma-separated list of valid OMIM numbers',
    format: vals => (vals || []).join(', '),
  },
  {
    field: 'rejectedGenes',
    header: 'Previously Tested Genes',
    isEditable: true,
    format: genes => (genes || []).map(gene => `${gene.gene}${gene.comments ? ` -- (${gene.comments})` : ''}`).join(', '),
    description: 'comma-separated list of genes',
  },
  {
    field: 'candidateGenes',
    header: 'Candidate Genes',
    isEditable: true,
    format: genes => (genes || []).map(gene => `${gene.gene}${gene.comments ? ` -- (${gene.comments})` : ''}`).join(', '),
    description: 'comma-separated list of genes',
  },
]

export const SHOW_IN_REVIEW = 'IN_REVIEW'
const SHOW_ACCEPTED = 'ACCEPTED'

const SHOW_DATA_LOADED = 'SHOW_DATA_LOADED'
const SHOW_PHENOTYPES_ENTERED = 'SHOW_PHENOTYPES_ENTERED'
const SHOW_NO_PHENOTYPES_ENTERED = 'SHOW_NO_PHENOTYPES_ENTERED'

const SHOW_ASSIGNED_TO_ME_IN_REVIEW = 'SHOW_ASSIGNED_TO_ME_IN_REVIEW'
const SHOW_ASSIGNED_TO_ME = 'SHOW_ASSIGNED_TO_ME'
const SHOW_ANALYSED_BY_ME = 'SHOW_ANALYSED_BY_ME'
const SHOW_ANALYSED = 'SHOW_ANALYSED'
const SHOW_NOT_ANALYSED = 'SHOW_NOT_ANALYSED'

const getFamilyCaseReviewStatuses  = (family, individualsByGuid) => {
  const statuses = family.individualGuids.map(
    individualGuid => (individualsByGuid[individualGuid] || {}).caseReviewStatus,
  ).filter(status => status)
  return statuses.length ? statuses : family.caseReviewStatuses
}

const caseReviewStatusFilter = status => individualsByGuid => family => getFamilyCaseReviewStatuses(
  family, individualsByGuid,
).some(caseReviewStatus => caseReviewStatus === status)

const familyIsInReview = (family, individualsByGuid) => getFamilyCaseReviewStatuses(family, individualsByGuid).every(
  status => status === CASE_REVIEW_STATUS_IN_REVIEW,
)

const familyIsAssignedToMe = (family, user) => (
  family.assignedAnalyst ? family.assignedAnalyst.email === user.email : null)

const REQUIRED_METADATA_FIELDS = INDIVIDUAL_DETAIL_FIELDS.filter(
  ({ isRequiredInternal }) => isRequiredInternal,
).map(({ field, subFields }) => (subFields ? subFields[0].field : field))

const familyHasRequiredMetadata = (family, individualsByGuid) => {
  const individuals = family.individualGuids.map(
    individualGuid => individualsByGuid[individualGuid],
  ).filter(individual => individual)
  return individuals.length ? individuals.some(individual => REQUIRED_METADATA_FIELDS.every(
    field => individual[field] || individual[field] === false,
  ) && individual.features.length > 0) : family.hasRequiredMetadata
}

const ALL_FAMILIES_FILTER = { value: SHOW_ALL, name: 'All', createFilter: () => () => (true) }
const IN_REVIEW_FAMILIES_FILTER = {
  value: SHOW_IN_REVIEW,
  name: 'In Review',
  createFilter: individualsByGuid => family => familyIsInReview(family, individualsByGuid),
}
const ACCEPTED_FILTER = {
  value: SHOW_ACCEPTED,
  name: 'Accepted',
  createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_ACCEPTED),
}
const ASSIGNED_TO_ME_FILTER = {
  value: SHOW_ASSIGNED_TO_ME,
  name: 'Assigned To Me',
  createFilter: (individualsByGuid, user) => family => familyIsAssignedToMe(family, user),
}
const ANALYST_HIGH_PRIORITY_TAG = 'Analyst high priority'

const hasMatchingSampleFilter = isMatchingSample => (individualsByGuid, user, samplesByFamily) => family => (
  (samplesByFamily[family.familyGuid] || []).some(sample => sample.isActive && isMatchingSample(sample)))

export const CATEGORY_FAMILY_FILTERS = {
  [FAMILY_FIELD_ANALYSIS_STATUS]: [
    ...SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS.map(option => ({
      ...option,
      createFilter: () => family => family.analysisStatus === option.value,
    })),
    ...[ACCEPTED_FILTER, IN_REVIEW_FAMILIES_FILTER].map(filter => ({ ...filter, category: 'Case Review Status' })),
  ],
  [FAMILY_FIELD_ANALYSED_BY]: [
    ASSIGNED_TO_ME_FILTER,
    {
      value: SHOW_ANALYSED_BY_ME,
      name: 'Analysed By Me',
      analysedByFilter: (individualsByGuid, user) => ({ createdBy }) => createdBy === (user.displayName || user.email),
    },
    {
      value: SHOW_ANALYSED,
      name: 'Analysed',
      analysedByFilter: () => () => true,
    },
    {
      value: SHOW_NOT_ANALYSED,
      name: 'Not Analysed',
      requireNoAnalysedBy: true,
      analysedByFilter: () => () => true,
    },
    ...FAMILY_ANALYSED_BY_DATA_TYPES.map(([type, typeDisplay]) => ({
      value: type,
      name: typeDisplay,
      category: 'Data Type',
      analysedByFilter: () => ({ dataType }) => dataType === type,
    })),
    {
      value: 'yearSinceAnalysed',
      name: '>1 Year',
      category: 'Analysis Date',
      requireNoAnalysedBy: true,
      analysedByFilter: () => ({ lastModifiedDate }) => (
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
      createFilter: hasMatchingSampleFilter(({ sampleType }) => sampleType === SAMPLE_TYPE_RNA),
    },
    ...[DATASET_TYPE_SV_CALLS, DATASET_TYPE_MITO_CALLS].map(dataType => ({
      value: `${SHOW_DATA_LOADED}_${dataType}`,
      name: `Data Loaded -${DATASET_TITLE_LOOKUP[dataType]}`,
      createFilter: hasMatchingSampleFilter(
        ({ sampleType, datasetType }) => sampleType !== SAMPLE_TYPE_RNA && datasetType === dataType,
      ),
    })),
    {
      value: SHOW_PHENOTYPES_ENTERED,
      name: 'Required Metadata Entered',
      createFilter: individualsByGuid => family => familyHasRequiredMetadata(family, individualsByGuid),
    },
    {
      value: SHOW_NO_PHENOTYPES_ENTERED,
      name: 'Required Metadata Missing',
      createFilter: individualsByGuid => family => !familyHasRequiredMetadata(family, individualsByGuid),
    },
  ],
  [FAMILY_FIELD_SAVED_VARIANTS]: [MME_TAG_NAME, ANALYST_HIGH_PRIORITY_TAG].map(tagName => ({
    value: tagName,
    name: tagName,
    createFilter: (individualsByGuid, user, samplesByFamily, familyTagTypeCounts) => ({ familyGuid }) => (
      (familyTagTypeCounts[familyGuid] || {})[tagName]
    ),
  })),
}

export const FAMILY_FILTER_LOOKUP = Object.values(CATEGORY_FAMILY_FILTERS).reduce(
  (acc, options) => {
    options.forEach((opt) => {
      acc[opt.value] = opt.createFilter
    })
    return acc
  }, {},
)

export const CASE_REVIEW_FAMILY_FILTER_OPTIONS = [
  ALL_FAMILIES_FILTER,
  {
    value: SHOW_ASSIGNED_TO_ME_IN_REVIEW,
    name: 'Assigned To Me - In Review',
    createFilter: (individualsByGuid, user) => family => familyIsAssignedToMe(
      family, user,
    ) && familyIsInReview(family, individualsByGuid),
  },
  { ...ASSIGNED_TO_ME_FILTER, name: 'Assigned To Me - All' },
  { ...IN_REVIEW_FAMILIES_FILTER, category: 'Case Review Status:' },
  { ...ACCEPTED_FILTER, category: 'Case Review Status:' },
  ...CASE_REVIEW_STATUS_OPTIONS.filter(
    ({ value }) => value !== CASE_REVIEW_STATUS_ACCEPTED && value !== CASE_REVIEW_STATUS_IN_REVIEW,
  ).map(({ name, value }) => ({
    value: `SHOW_${name.toUpperCase()}`,
    category: 'Case Review Status:',
    name,
    createFilter: caseReviewStatusFilter(value),
  })),
]

export const CASE_REVIEW_FILTER_LOOKUP = CASE_REVIEW_FAMILY_FILTER_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.createFilter,
  }), {},
)

export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_FAMILY_ADDED_DATE = 'FAMILY_ADDED_DATE'
const SORT_BY_DATA_LOADED_DATE = 'DATA_LOADED_DATE'
const SORT_BY_DATA_FIRST_LOADED_DATE = 'DATA_FIRST_LOADED_DATE'
const SORT_BY_REVIEW_STATUS_CHANGED_DATE = 'REVIEW_STATUS_CHANGED_DATE'
const SORT_BY_ANALYSIS_STATUS = 'SORT_BY_ANALYSIS_STATUS'
const SORT_BY_ANALYSED_DATE = 'SORT_BY_ANALYSED_DATE'

const FAMILY_ANALYSIS_STATUS_SORT_LOOKUP = ALL_FAMILY_ANALYSIS_STATUS_OPTIONS.reduce(
  (acc, { value }, i) => ({ ...acc, [value]: i.toString(36) }), {},
)

export const FAMILY_SORT_OPTIONS = [
  {
    value: SORT_BY_FAMILY_NAME,
    name: 'Family Name',
    createSortKeyGetter: () => family => family.displayName,
  },
  {
    value: SORT_BY_FAMILY_ADDED_DATE,
    name: 'Date Added',
    createSortKeyGetter: () => family => family.createdDate,
  },
  {
    value: SORT_BY_DATA_LOADED_DATE,
    name: 'Date Loaded',
    createSortKeyGetter: (individualsByGuid, samplesByFamily) => (family) => {
      const loadedSamples = samplesByFamily[family.familyGuid] || []
      return loadedSamples.length ? loadedSamples[loadedSamples.length - 1].loadedDate : '2000-01-01T01:00:00.000Z'
    },
  },
  {
    value: SORT_BY_DATA_FIRST_LOADED_DATE,
    name: 'Date First Loaded',
    createSortKeyGetter: (individualsByGuid, samplesByFamily) => (family) => {
      const loadedSamples = samplesByFamily[family.familyGuid] || []
      return loadedSamples.length ? loadedSamples[0].loadedDate : '2000-01-01T01:00:00.000Z'
    },
  },
  {
    value: SORT_BY_ANALYSIS_STATUS,
    name: 'Analysis Status',
    createSortKeyGetter: () => family => FAMILY_ANALYSIS_STATUS_SORT_LOOKUP[family.analysisStatus] || '',
  },
  {
    value: SORT_BY_ANALYSED_DATE,
    name: 'Date Last Analysed',
    createSortKeyGetter: () => family => family.analysedBy.filter(({ dataType }) => dataType === SNP_DATA_TYPE).map(
      ({ lastModifiedDate }) => lastModifiedDate,
    ).sort().reverse()[0] || '2000-01-01T01:00:00.000Z',
  },
  {
    value: SORT_BY_REVIEW_STATUS_CHANGED_DATE,
    name: 'Date Review Status Changed',
    createSortKeyGetter: individualsByGuid => (family) => {
      const lastModified = family.individualGuids.map(
        individualGuid => (individualsByGuid[individualGuid] || {}).caseReviewStatusLastModifiedDate,
      ).filter(status => status)
      return lastModified.length ? lastModified.reduce(
        (acc, status) => (status > acc ? status : acc), '2000-01-01T01:00:00.000Z',
      ) : family.caseReviewStatusLastModified || '2000-01-01T01:00:00.000Z'
    },
  },
]

const tableConfigForField = fieldConfigs => (field) => {
  const  { label, width, formFieldProps = {} } = fieldConfigs[field]
  return { name: field,  content: label, width, formFieldProps }
}

const formatNotes = notes => (notes || []).map(({ note }) => stripMarkdown(note)).join(';')

const FAMILY_FIELD_CONFIGS = Object.entries({
  [FAMILY_FIELD_ID]: { label: 'Family ID', width: 2 },
  [FAMILY_DISPLAY_NAME]: { label: 'Display Name', width: 3, description: 'The human-readable family name to show in place of the family ID' },
  [FAMILY_FIELD_CREATED_DATE]: { label: 'Created Date' },
  [FAMILY_FIELD_FIRST_SAMPLE]: { label: 'First Data Loaded Date', format: firstSample => (firstSample || {}).loadedDate },
  [FAMILY_FIELD_DESCRIPTION]: { label: 'Description', format: stripMarkdown, width: 8, description: 'A short description of the family' },
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    format: status => (FAMILY_ANALYSIS_STATUS_LOOKUP[status] || {}).name,
  },
  [FAMILY_FIELD_ASSIGNED_ANALYST]: { format: analyst => (analyst ? analyst.email : '') },
  [FAMILY_FIELD_ANALYSED_BY]: { format: analysedBy => analysedBy.map(o => o.createdBy).join(',') },
  [FAMILY_FIELD_CODED_PHENOTYPE]: { width: 4, description: "High level summary of the family's phenotype/disease" },
  [FAMILY_FIELD_MONDO_ID]: { width: 3, description: 'MONDO Disease Ontology ID' },
  ...FAMILY_NOTES_FIELDS.reduce((acc, { id }) => ({ ...acc, [id]: { format: formatNotes } }), {}),
}).reduce((acc, [field, config]) => ({ ...acc, [field]: { label: FAMILY_FIELD_NAME_LOOKUP[field], ...config } }), {})

export const FAMILY_FIELDS = [
  FAMILY_FIELD_ID, FAMILY_FIELD_DESCRIPTION, FAMILY_FIELD_CODED_PHENOTYPE, FAMILY_FIELD_MONDO_ID,
].map(tableConfigForField(FAMILY_FIELD_CONFIGS))

export const FAMILY_EXPORT_DATA = [
  FAMILY_FIELD_ID,
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_CREATED_DATE,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ASSIGNED_ANALYST,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_CASE_NOTES,
].map(exportConfigForField(FAMILY_FIELD_CONFIGS))

export const FAMILY_BULK_EDIT_EXPORT_DATA = [
  FAMILY_FIELD_ID,
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_CODED_PHENOTYPE,
  FAMILY_FIELD_MONDO_ID,
].map(exportConfigForField(FAMILY_FIELD_CONFIGS))

export const INDIVIDUAL_FIELDS = [
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
  INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP,
].map(tableConfigForField(INDIVIDUAL_FIELD_CONFIGS))

export const INDIVIDUAL_DETAIL_EXPORT_DATA = [
  ...INDIVIDUAL_HPO_EXPORT_DATA,
  ...INDIVIDUAL_DETAIL_FIELDS.reduce((acc, { isEditable, isCollaboratorEditable, isPrivate, subFields, ...field }) => {
    if (isPrivate || !isEditable || field.field === 'features') {
      return acc
    }
    const fields = subFields || [field]
    return [...acc, ...fields]
  }, []),
]

export const CASE_REVIEW_FAMILY_EXPORT_DATA = [
  ...FAMILY_EXPORT_DATA,
  { header: 'Internal Case Review Summary', field: FAMILY_FIELD_INTERNAL_SUMMARY, format: stripMarkdown },
  { header: 'Internal Case Review Notes', field: FAMILY_FIELD_INTERNAL_NOTES, format: stripMarkdown },
]

export const INDIVIDUAL_NOTES_CONFIG = tableConfigForField(INDIVIDUAL_FIELD_CONFIGS)(INDIVIDUAL_FIELD_NOTES)

export const CASE_REVIEW_INDIVIDUAL_EXPORT_DATA = [
  ...INDIVIDUAL_EXPORT_DATA,
  { header: 'Case Review Status', field: 'caseReviewStatus', format: status => CASE_REVIEW_STATUS_OPT_LOOKUP[status].name },
  { header: 'Case Review Status Last Modified', field: 'caseReviewStatusLastModifiedDate' },
  { header: 'Case Review Status Last Modified By', field: 'caseReviewStatusLastModifiedBy' },
  { header: 'Case Review Discussion', field: 'caseReviewDiscussion', format: stripMarkdown },
]

export const SAMPLE_EXPORT_DATA = [
  { header: 'Family ID', field: 'familyId' },
  { header: 'Individual ID', field: 'individualId' },
  { header: 'Sample ID', field: 'sampleId' },
  { header: 'Loaded Date', field: 'loadedDate' },
  { header: 'Sample Type', field: 'sampleType' },
]

export const TAG_FIELD_NAME = 'tags'

export const TAG_FORM_FIELD = {
  name: TAG_FIELD_NAME,
  label: 'Tags',
  includeCategories: true,
  format: value => (value || []).map(({ name }) => name),
  parse: value => (value || []).map(name => ({ name })),
  validate: value => (value && value.length ? undefined : 'Required'),
}

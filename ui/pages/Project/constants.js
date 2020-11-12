/* eslint-disable no-multi-spaces */

import { stripMarkdown } from 'shared/utils/stringUtils'
import {
  FAMILY_STATUS_SOLVED,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_SOLVED_NOVEL_GENE,
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE,
  FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES,
  FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE,
  FAMILY_STATUS_CLOSED,
  FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
  FAMILY_FIELD_ID,
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ASSIGNED_ANALYST,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_CREATED_DATE,
  FAMILY_FIELD_CODED_PHENOTYPE,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
  INDIVIDUAL_FIELD_NOTES,
  INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP,
  FAMILY_ANALYSIS_STATUS_OPTIONS,
  INDIVIDUAL_FIELD_CONFIGS,
  INDIVIDUAL_HPO_EXPORT_DATA,
  SHOW_ALL,
  familyVariantSamples,
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
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED,                name: 'Not Accepted',          color: '#4f5cb3' },  //#C5CAE9
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED,            name: 'More Info Needed',      color: '#F44336' },  //#673AB7
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

export const SHOW_IN_REVIEW = 'IN_REVIEW'
const SHOW_ACCEPTED = 'ACCEPTED'

const SHOW_SOLVED = 'SHOW_SOLVED'
const SHOW_STRONG_CANDIDATE = 'SHOW_STRONG_CANDIDATE'
const SHOW_REVIEWED_NO_CLEAR_CANDIDATE = 'SHOW_REVIEWED_NO_CLEAR_CANDIDATE'
const SHOW_ANALYSIS_IN_PROGRESS = 'SHOW_ANALYSIS_IN_PROGRESS'

const SHOW_DATA_LOADED = 'SHOW_DATA_LOADED'
const SHOW_PHENOTYPES_ENTERED = 'SHOW_PHENOTYPES_ENTERED'
const SHOW_NO_PHENOTYPES_ENTERED = 'SHOW_NO_PHENOTYPES_ENTERED'

const SHOW_ASSIGNED_TO_ME_IN_REVIEW = 'SHOW_ASSIGNED_TO_ME_IN_REVIEW'
const SHOW_ASSIGNED_TO_ME = 'SHOW_ASSIGNED_TO_ME'
const SHOW_ANALYSED_BY_ME = 'SHOW_ANALYSED_BY_ME'
const SHOW_NOT_ANALYSED_BY_ME = 'SHOW_NOT_ANALYSED_BY_ME'
const SHOW_ANALYSED_BY_CMG = 'SHOW_ANALYSED_BY_CMG'
const SHOW_NOT_ANALYSED_BY_CMG = 'SHOW_NOT_ANALYSED_BY_CMG'
const SHOW_ANALYSED = 'SHOW_ANALYSED'
const SHOW_NOT_ANALYSED = 'SHOW_NOT_ANALYSED'
const SHOW_CLOSED = 'SHOW_CLOSED'


const SOLVED_STATUSES = new Set([
  FAMILY_STATUS_SOLVED,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_SOLVED_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_SOLVED_NOVEL_GENE,
])

const STRONG_CANDIDATE_STATUSES = new Set([
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_KNOWN_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_KNOWN_GENE_DIFFERENT_PHENOTYPE,
  FAMILY_STATUS_STRONG_CANDIDATE_NOVEL_GENE,
])

const ANALYSIS_IN_PROGRESS_STATUSES = new Set([
  FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
  FAMILY_STATUS_REVIEWED_PURSUING_CANDIDATES,
])

const caseReviewStatusFilter = status => individualsByGuid => family =>
  family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).some(
    individual => individual.caseReviewStatus === status,
  )

const familyIsInReview = (family, individualsByGuid) =>
  family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).every(
    individual => individual.caseReviewStatus === CASE_REVIEW_STATUS_IN_REVIEW,
  )

const familyIsAssignedToMe = (family, user) =>
  (family.assignedAnalyst ? family.assignedAnalyst.email === user.email : null)

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
  createFilter: (individualsByGuid, samplesByGuid, user) => family => familyIsAssignedToMe(family, user),
}

export const FAMILY_FILTER_OPTIONS = [
  ALL_FAMILIES_FILTER,
  {
    value: SHOW_DATA_LOADED,
    category: 'Data Status:',
    name: 'Data Loaded',
    createFilter: (individualsByGuid, samplesByGuid) => family =>
      familyVariantSamples(family, individualsByGuid, samplesByGuid).filter(sample => sample.isActive).length > 0,
  },
  {
    value: SHOW_PHENOTYPES_ENTERED,
    category: 'Data Status:',
    name: 'Phenotypes Entered',
    createFilter: individualsByGuid => family =>
      family.individualGuids.some(individualGuid => (individualsByGuid[individualGuid].features || []).length > 0),
  },
  {
    value: SHOW_NO_PHENOTYPES_ENTERED,
    category: 'Data Status:',
    name: 'No Phenotypes Entered',
    createFilter: individualsByGuid => family =>
      family.individualGuids.every(individualGuid => (individualsByGuid[individualGuid].features || []).length < 1),
  },
  { ...ASSIGNED_TO_ME_FILTER, category: 'Analysed By:' },
  {
    value: SHOW_ANALYSED_BY_ME,
    category: 'Analysed By:',
    name: 'Analysed By Me',
    createFilter: (individualsByGuid, samplesByGuid, user) => family =>
      family.analysedBy.map(analysedBy => analysedBy.createdBy.email).includes(user.email),
  },
  {
    value: SHOW_NOT_ANALYSED_BY_ME,
    category: 'Analysed By:',
    name: 'Not Analysed By Me',
    createFilter: (individualsByGuid, samplesByGuid, user) => family =>
      !family.analysedBy.map(analysedBy => analysedBy.createdBy.email).includes(user.email),
  },
  {
    value: SHOW_ANALYSED_BY_CMG,
    category: 'Analysed By:',
    name: 'Analysed By CMG',
    createFilter: () => family =>
      family.analysedBy.some(analysedBy => analysedBy.createdBy.isStaff),
  },
  {
    value: SHOW_NOT_ANALYSED_BY_CMG,
    category: 'Analysed By:',
    name: 'Not Analysed By CMG',
    createFilter: () => family =>
      family.analysedBy.every(analysedBy => !analysedBy.createdBy.isStaff),
  },
  {
    value: SHOW_ANALYSED,
    category: 'Analysed By:',
    name: 'Analysed',
    createFilter: () => family => family.analysedBy.length > 0,
  },
  {
    value: SHOW_NOT_ANALYSED,
    category: 'Analysed By:',
    name: 'Not Analysed',
    createFilter: () => family => family.analysedBy.length < 1,
  },
  {
    value: SHOW_SOLVED,
    category: 'Analysis Status:',
    name: 'Solved',
    createFilter: () => family =>
      SOLVED_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_STRONG_CANDIDATE,
    category: 'Analysis Status:',
    name: 'Strong Candidate',
    createFilter: () => family =>
      STRONG_CANDIDATE_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_REVIEWED_NO_CLEAR_CANDIDATE,
    category: 'Analysis Status:',
    name: 'No Clear Candidate',
    createFilter: () => family => family.analysisStatus === FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE,
  },
  {
    value: SHOW_CLOSED,
    category: 'Analysis Status:',
    name: 'Closed',
    createFilter: () => family => family.analysisStatus === FAMILY_STATUS_CLOSED,
  },
  {
    value: SHOW_ANALYSIS_IN_PROGRESS,
    category: 'Analysis Status:',
    name: 'Analysis In Progress',
    createFilter: () => family =>
      ANALYSIS_IN_PROGRESS_STATUSES.has(family.analysisStatus),
  },
  { ...ACCEPTED_FILTER, category: 'Analysis Status:' },
  { ...IN_REVIEW_FAMILIES_FILTER, category: 'Analysis Status:' },
]

export const INTERNAL_FAMILY_FILTER_OPTIONS = [
  ALL_FAMILIES_FILTER,
  {
    value: SHOW_ASSIGNED_TO_ME_IN_REVIEW,
    name: 'Assigned To Me - In Review',
    createFilter: (individualsByGuid, samplesByGuid, user) => family =>
      familyIsAssignedToMe(family, user) && familyIsInReview(family, individualsByGuid),
  },
  { ...ASSIGNED_TO_ME_FILTER, name: 'Assigned To Me - All' },
  { ...IN_REVIEW_FAMILIES_FILTER, category: 'Case Review Status:' },
  { ...ACCEPTED_FILTER, category: 'Case Review Status:' },
  ...CASE_REVIEW_STATUS_OPTIONS.filter(({ value }) =>
    value !== CASE_REVIEW_STATUS_ACCEPTED && value !== CASE_REVIEW_STATUS_IN_REVIEW,
  ).map(({ name, value }) => ({
    value: `SHOW_${name.toUpperCase()}`,
    category: 'Case Review Status:',
    name,
    createFilter: caseReviewStatusFilter(value),
  })),
]

export const FAMILY_FILTER_LOOKUP = [...FAMILY_FILTER_OPTIONS, ...INTERNAL_FAMILY_FILTER_OPTIONS].reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt,
  }), {},
)


export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_FAMILY_ADDED_DATE = 'FAMILY_ADDED_DATE'
const SORT_BY_DATA_LOADED_DATE = 'DATA_LOADED_DATE'
const SORT_BY_DATA_FIRST_LOADED_DATE = 'DATA_FIRST_LOADED_DATE'
const SORT_BY_REVIEW_STATUS_CHANGED_DATE = 'REVIEW_STATUS_CHANGED_DATE'
const SORT_BY_ANALYSIS_STATUS = 'SORT_BY_ANALYSIS_STATUS'
const SORT_BY_ANALYSED_DATE = 'SORT_BY_ANALYSED_DATE'

export const FAMILY_SORT_OPTIONS = [
  {
    value: SORT_BY_FAMILY_NAME,
    name: 'Family Name',
    createSortKeyGetter: () => family => family.displayName,
  },
  {
    value: SORT_BY_FAMILY_ADDED_DATE,
    name: 'Date Added',
    createSortKeyGetter: individualsByGuid => family =>
      family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).reduce(
        (acc, individual) => {
          const indivCreatedDate = individual.createdDate || '2000-01-01T01:00:00.000Z'
          return indivCreatedDate > acc ? indivCreatedDate : acc
        },
        '2000-01-01T01:00:00.000Z',
      ),
  },
  {
    value: SORT_BY_DATA_LOADED_DATE,
    name: 'Date Loaded',
    createSortKeyGetter: (individualsByGuid, samplesByGuid) => (family) => {
      const loadedSamples = familyVariantSamples(family, individualsByGuid, samplesByGuid)
      return loadedSamples.length ? loadedSamples[loadedSamples.length - 1].loadedDate : '2000-01-01T01:00:00.000Z'
    },
  },
  {
    value: SORT_BY_DATA_FIRST_LOADED_DATE,
    name: 'Date First Loaded',
    createSortKeyGetter: (individualsByGuid, samplesByGuid) => (family) => {
      const loadedSamples = familyVariantSamples(family, individualsByGuid, samplesByGuid)
      return loadedSamples.length ? loadedSamples[0].loadedDate : '2000-01-01T01:00:00.000Z'
    },
  },
  {
    value: SORT_BY_ANALYSIS_STATUS,
    name: 'Analysis Status',
    createSortKeyGetter: () => family =>
      FAMILY_ANALYSIS_STATUS_OPTIONS.map(status => status.value).indexOf(family.analysisStatus),
  },
  {
    value: SORT_BY_ANALYSED_DATE,
    name: 'Date Last Analysed',
    createSortKeyGetter: () => family =>
      family.analysedBy.map(
        ({ lastModifiedDate }) => lastModifiedDate,
      ).sort()[family.analysedBy.length - 1] || '3000-01-01T01:00:00.000Z',
  },
  {
    value: SORT_BY_REVIEW_STATUS_CHANGED_DATE,
    name: 'Date Review Status Changed',
    createSortKeyGetter: individualsByGuid => family =>
      family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).reduce(
        (acc, individual) => {
          const indivCaseReviewStatusLastModifiedDate = individual.caseReviewStatusLastModifiedDate || '2000-01-01T01:00:00.000Z'
          return indivCaseReviewStatusLastModifiedDate > acc ? indivCaseReviewStatusLastModifiedDate : acc
        },
        '2000-01-01T01:00:00.000Z',
      ),
  },
]

const exportConfigForField = fieldConfigs => (field) => {
  const  { label, format, description } = fieldConfigs[field]
  return { field,  header: label, format, description }
}

const tableConfigForField = fieldConfigs => (field) => {
  const  { label, width, formFieldProps = {} } = fieldConfigs[field]
  return { name: field,  content: label, width, formFieldProps }
}

const FAMILY_FIELD_CONFIGS = {
  [FAMILY_FIELD_ID]: { label: 'Family ID', width: 2 },
  [FAMILY_DISPLAY_NAME]: { label: 'Display Name', width: 3, description: 'The human-readable family name to show in place of the family ID' },
  [FAMILY_FIELD_CREATED_DATE]: { label: 'Created Date' },
  [FAMILY_FIELD_FIRST_SAMPLE]: { label: 'First Data Loaded Date', format: firstSample => (firstSample || {}).loadedDate },
  [FAMILY_FIELD_DESCRIPTION]: { label: 'Description', format: stripMarkdown, width: 10, description: 'A short description of the family' },
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    label: 'Analysis Status',
    format: status => (FAMILY_ANALYSIS_STATUS_OPTIONS.find(option => option.value === status) || {}).name,
  },
  [FAMILY_FIELD_ASSIGNED_ANALYST]: { label: 'Assigned Analyst' },
  [FAMILY_FIELD_ANALYSED_BY]: { label: 'Analysed By', format: analysedBy => analysedBy.map(o => o.createdBy.fullName || o.createdBy.email).join(',') },
  [FAMILY_FIELD_ANALYSIS_SUMMARY]: { label: 'Analysis Summary', format: stripMarkdown },
  [FAMILY_FIELD_ANALYSIS_NOTES]: { label: 'Analysis Notes', format: stripMarkdown },
  [FAMILY_FIELD_CODED_PHENOTYPE]: { label: 'Coded Phenotype', width: 4, description: "High level summary of the family's phenotype/disease" },
}

export const FAMILY_FIELDS = [
  FAMILY_FIELD_ID, FAMILY_FIELD_DESCRIPTION, FAMILY_FIELD_CODED_PHENOTYPE,
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
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_ANALYSIS_NOTES,
].map(exportConfigForField(FAMILY_FIELD_CONFIGS))

export const FAMILY_BULK_EDIT_EXPORT_DATA = [
  FAMILY_FIELD_ID,
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_CODED_PHENOTYPE,
].map(exportConfigForField(FAMILY_FIELD_CONFIGS))


export const INDIVIDUAL_HAS_DATA_FIELD = 'hasLoadedSamples'
const INDIVIDUAL_HAS_DATA_EXPORT_CONFIG = {
  field: INDIVIDUAL_HAS_DATA_FIELD,
  header: 'Individual Data Loaded',
  format: hasData => (hasData ? 'Yes' : 'No'),
}

export const INDIVIDUAL_FIELDS = [
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
  INDIVIDUAL_FIELD_PROBAND_RELATIONSHIP,
].map(tableConfigForField(INDIVIDUAL_FIELD_CONFIGS))

export const INTERNAL_FAMILY_EXPORT_DATA = [
  { header: 'Internal Case Review Summary', field: FAMILY_FIELD_INTERNAL_SUMMARY, format: stripMarkdown },
  { header: 'Internal Case Review Notes', field: FAMILY_FIELD_INTERNAL_NOTES, format: stripMarkdown },
]
export const INDIVIDUAL_NOTES_CONFIG = tableConfigForField(INDIVIDUAL_FIELD_CONFIGS)(INDIVIDUAL_FIELD_NOTES)

export const INDIVIDUAL_ID_EXPORT_DATA = [
  FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID,
].map(exportConfigForField(INDIVIDUAL_FIELD_CONFIGS))

const INDIVIDUAL_CORE_EXPORT_DATA = [
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


export const INTERNAL_INDIVIDUAL_EXPORT_DATA = [
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

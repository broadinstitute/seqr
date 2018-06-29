/* eslint-disable no-multi-spaces */

import orderBy from 'lodash/orderBy'

import { hasPhenotipsDetails } from 'shared/components/panel/view-phenotips-info/PhenotipsDataPanel'
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
  FAMILY_STATUS_ANALYSIS_IN_PROGRESS,
  CLINSIG_SEVERITY,
  FAMILY_ANALYSIS_STATUS_OPTIONS,
  SAMPLE_STATUS_LOADED,
  DATASET_TYPE_VARIANT_CALLS,
  SEX_LOOKUP,
  AFFECTED_LOOKUP,
} from 'shared/utils/constants'

export const CASE_REVIEW_TABLE_NAME = 'Case Review'

export const CASE_REVIEW_STATUS_NOT_IN_REVIEW = 'N'
export const CASE_REVIEW_STATUS_IN_REVIEW = 'I'
export const CASE_REVIEW_STATUS_UNCERTAIN = 'U'
export const CASE_REVIEW_STATUS_ACCEPTED = 'A'
export const CASE_REVIEW_STATUS_NOT_ACCEPTED = 'R'
export const CASE_REVIEW_STATUS_MORE_INFO_NEEDED = 'Q'
export const CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS = 'P'
export const CASE_REVIEW_STATUS_WAITLIST = 'W'
export const CASE_REVIEW_STATUS_WITHDREW = 'WD'
export const CASE_REVIEW_STATUS_INELIGIBLE = 'IE'
export const CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE = 'DP'

export const CASE_REVIEW_STATUS_OPTIONS = [
  { value: CASE_REVIEW_STATUS_IN_REVIEW,                   name: 'In Review',             color: '#2196F3' },
  { value: CASE_REVIEW_STATUS_UNCERTAIN,                   name: 'Uncertain',             color: '#fddb28' },
  { value: CASE_REVIEW_STATUS_ACCEPTED,                    name: 'Accepted',              color: '#8BC34A' },
  { value: CASE_REVIEW_STATUS_NOT_ACCEPTED,                name: 'Not Accepted',          color: '#4f5cb3' },  //#C5CAE9
  { value: CASE_REVIEW_STATUS_MORE_INFO_NEEDED,            name: 'More Info Needed',      color: '#F44336' },  //#673AB7
  { value: CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS, name: 'Pending Results and Records', color: '#996699' },
  { value: CASE_REVIEW_STATUS_NOT_IN_REVIEW,               name: 'Not In Review',         color: '#118833' },
  { value: CASE_REVIEW_STATUS_WAITLIST,                    name: 'Waitlist',              color: '#990099' },
  { value: CASE_REVIEW_STATUS_WITHDREW,                    name: 'Withdrew',              color: '#999999' },
  { value: CASE_REVIEW_STATUS_INELIGIBLE,                  name: 'Ineligible',            color: '#111111' },
  { value: CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE,     name: 'Declined To Participate', color: '#FF8800' },
]

export const CASE_REVIEW_STATUS_OPT_LOOKUP = CASE_REVIEW_STATUS_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    ...{ [opt.value]: opt },
  }), {},
)

export const SHOW_ALL = 'ALL'

export const SHOW_IN_REVIEW = 'IN_REVIEW'
export const SHOW_ACCEPTED = 'ACCEPTED'
export const SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
export const SHOW_UNCERTAIN = 'UNCERTAIN'
export const SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

export const SHOW_SOLVED = 'SHOW_SOLVED'
export const SHOW_STRONG_CANDIDATE = 'SHOW_STRONG_CANDIDATE'
export const SHOW_REVIEWED_NO_CLEAR_CANDIDATE = 'SHOW_REVIEWED_NO_CLEAR_CANDIDATE'
export const SHOW_ANALYSIS_IN_PROGRESS = 'SHOW_ANALYSIS_IN_PROGRESS'

export const SHOW_NOT_IN_REVIEW = 'NOT_IN_REVIEW'
export const SHOW_PENDING_RESULTS_AND_RECORDS = 'PENDING_RESULTS_AND_RECORDS'
export const SHOW_WAITLIST = 'WAITLIST'
export const SHOW_WITHDREW = 'WITHDREW'
export const SHOW_INELIGIBLE = 'INELIGIBLE'
export const SHOW_DECLINED_TO_PARTICIPATE = 'DECLINED_TO_PARTICIPATE'

export const SHOW_DATA_LOADED = 'SHOW_DATA_LOADED'
export const SHOW_PHENOTYPES_ENTERED = 'SHOW_PHENOTYPES_ENTERED'
export const SHOW_NO_PHENOTYPES_ENTERED = 'SHOW_NO_PHENOTYPES_ENTERED'

export const SHOW_ANALYSED_BY_ME = 'SHOW_ANALYSED_BY_ME'
export const SHOW_NOT_ANALYSED_BY_ME = 'SHOW_NOT_ANALYSED_BY_ME'
export const SHOW_ANALYSED_BY_CMG = 'SHOW_ANALYSED_BY_CMG'
export const SHOW_NOT_ANALYSED_BY_CMG = 'SHOW_NOT_ANALYSED_BY_CMG'
export const SHOW_ANALYSED = 'SHOW_ANALYSED'
export const SHOW_NOT_ANALYSED = 'SHOW_NOT_ANALYSED'


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

export const familySamplesLoaded = (family, individualsByGuid, samplesByGuid) => {
  const loadedSamples = [...family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).reduce(
    (acc, individual) => new Set([...acc, ...individual.sampleGuids]), new Set(),
  )].map(sampleGuid => samplesByGuid[sampleGuid]).filter(sample =>
    sample.datasetType === DATASET_TYPE_VARIANT_CALLS &&
    sample.sampleStatus === SAMPLE_STATUS_LOADED &&
    sample.loadedDate,
  )
  return orderBy(loadedSamples, [s => s.loadedDate], 'asc')
}

export const FAMILY_FILTER_OPTIONS = [
  {
    value: SHOW_ALL,
    name: 'All',
    createFilter: () => () => (true),
  },
  {
    value: SHOW_DATA_LOADED,
    category: 'Data Status:',
    name: 'Data Loaded',
    internalOmit: true,
    createFilter: (individualsByGuid, samplesByGuid) => family =>
      familySamplesLoaded(family, individualsByGuid, samplesByGuid).length > 0,
  },
  {
    value: SHOW_PHENOTYPES_ENTERED,
    category: 'Data Status:',
    name: 'Phenotypes Entered',
    internalOmit: true,
    createFilter: individualsByGuid => family =>
      family.individualGuids.map(individualGuid => individualsByGuid[individualGuid].phenotipsData).some(
        phenotipsData => hasPhenotipsDetails(phenotipsData),
      ),
  },
  {
    value: SHOW_NO_PHENOTYPES_ENTERED,
    category: 'Data Status:',
    name: 'No Phenotypes Entered',
    internalOmit: true,
    createFilter: individualsByGuid => family =>
      family.individualGuids.map(individualGuid => individualsByGuid[individualGuid].phenotipsData).every(
        phenotipsData => !hasPhenotipsDetails(phenotipsData),
      ),
  },
  {
    value: SHOW_ANALYSED_BY_ME,
    category: 'Analysed By:',
    name: 'Analysed By Me',
    internalOmit: true,
    createFilter: (individualsByGuid, samplesByGuid, user) => family =>
      family.analysedBy.map(analysedBy => analysedBy.user.username).includes(user.username),
  },
  {
    value: SHOW_NOT_ANALYSED_BY_ME,
    category: 'Analysed By:',
    name: 'Not Analysed By Me',
    internalOmit: true,
    createFilter: (individualsByGuid, samplesByGuid, user) => family =>
      !family.analysedBy.map(analysedBy => analysedBy.user.username).includes(user.username),
  },
  {
    value: SHOW_ANALYSED_BY_CMG,
    category: 'Analysed By:',
    name: 'Analysed By CMG',
    internalOmit: true,
    createFilter: () => family =>
      family.analysedBy.some(analysedBy => analysedBy.user.is_staff),
  },
  {
    value: SHOW_NOT_ANALYSED_BY_CMG,
    category: 'Analysed By:',
    name: 'Not Analysed By CMG',
    internalOmit: true,
    createFilter: () => family =>
      family.analysedBy.every(analysedBy => !analysedBy.user.is_staff),
  },
  {
    value: SHOW_ANALYSED,
    category: 'Analysed By:',
    name: 'Analysed',
    internalOmit: true,
    createFilter: () => family => family.analysedBy.length > 0,
  },
  {
    value: SHOW_NOT_ANALYSED,
    category: 'Analysed By:',
    name: 'Not Analysed',
    internalOmit: true,
    createFilter: () => family => family.analysedBy.length < 1,
  },
  {
    value: SHOW_SOLVED,
    category: 'Analysis Status:',
    name: 'Solved',
    internalOmit: true,
    createFilter: () => family =>
      SOLVED_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_STRONG_CANDIDATE,
    category: 'Analysis Status:',
    name: 'Strong Candidate',
    internalOmit: true,
    createFilter: () => family =>
      STRONG_CANDIDATE_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_REVIEWED_NO_CLEAR_CANDIDATE,
    category: 'Analysis Status:',
    name: 'No Clear Candidate',
    internalOmit: true,
    createFilter: () => family => family.analysisStatus === FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE,
  },
  {
    value: SHOW_ANALYSIS_IN_PROGRESS,
    category: 'Analysis Status:',
    name: 'Analysis In Progress',
    internalOmit: true,
    createFilter: () => family =>
      ANALYSIS_IN_PROGRESS_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_ACCEPTED,
    category: 'Analysis Status:',
    name: 'Accepted',
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_ACCEPTED),
  },
  {
    value: SHOW_NOT_ACCEPTED,
    category: 'Analysis Status:',
    name: 'Not Accepted',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_NOT_ACCEPTED),
  },
  {
    value: SHOW_IN_REVIEW,
    category: 'Analysis Status:',
    name: 'In Review',
    createFilter: individualsByGuid => family =>
      family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).every(
        individual => individual.caseReviewStatus === CASE_REVIEW_STATUS_IN_REVIEW,
      ),
  },
  {
    value: SHOW_UNCERTAIN,
    category: 'Analysis Status:',
    name: 'Uncertain',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_UNCERTAIN),
  },
  {
    value: SHOW_MORE_INFO_NEEDED,
    category: 'Analysis Status:',
    name: 'More Info Needed',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_MORE_INFO_NEEDED),
  },
  {
    value: SHOW_NOT_IN_REVIEW,
    category: 'Analysis Status:',
    name: 'Not In Review',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_NOT_IN_REVIEW),
  },
  {
    value: SHOW_PENDING_RESULTS_AND_RECORDS,
    category: 'Analysis Status:',
    name: 'Pending Results and Records',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS),
  },
  {
    value: SHOW_WAITLIST,
    category: 'Analysis Status:',
    name: 'Waitlist',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_WAITLIST),
  },
  {
    value: SHOW_WITHDREW,
    category: 'Analysis Status:',
    name: 'Withdrew',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_WITHDREW),
  },
  {
    value: SHOW_INELIGIBLE,
    category: 'Analysis Status:',
    name: 'Ineligible',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_INELIGIBLE),
  },
  {
    value: SHOW_DECLINED_TO_PARTICIPATE,
    category: 'Analysis Status:',
    name: 'Declined to Participate',
    internalOnly: true,
    createFilter: caseReviewStatusFilter(CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE),
  },
]


export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_FAMILY_ADDED_DATE = 'FAMILY_ADDED_DATE'
export const SORT_BY_DATA_LOADED_DATE = 'DATA_LOADED_DATE'
export const SORT_BY_DATA_FIRST_LOADED_DATE = 'DATA_FIRST_LOADED_DATE'
export const SORT_BY_ANALYSIS_STATUS = 'SORT_BY_ANALYSIS_STATUS'

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
      const loadedSamples = familySamplesLoaded(family, individualsByGuid, samplesByGuid)
      return loadedSamples.length ? loadedSamples[loadedSamples.length - 1].loadedDate : '2000-01-01T01:00:00.000Z'
    },
  },
  {
    value: SORT_BY_DATA_FIRST_LOADED_DATE,
    name: 'Date First Loaded',
    createSortKeyGetter: (individualsByGuid, samplesByGuid) => (family) => {
      const loadedSamples = familySamplesLoaded(family, individualsByGuid, samplesByGuid)
      return loadedSamples.length ? loadedSamples[0].loadedDate : '2000-01-01T01:00:00.000Z'
    },
  },
  {
    value: SORT_BY_ANALYSIS_STATUS,
    name: 'Analysis Status',
    createSortKeyGetter: () => family =>
      FAMILY_ANALYSIS_STATUS_OPTIONS.map(status => status.value).indexOf(family.analysisStatus),
  },
]

export const FAMILY_EXPORT_DATA = [
  { header: 'Family ID', field: 'familyId' },
  { header: 'Display Name', field: 'displayName' },
  { header: 'Created Date', field: 'createdDate' },
  { header: 'First Data Loaded Date', field: 'firstSample', format: firstSample => (firstSample || {}).loadedDate },
  { header: 'Description', field: 'description', format: stripMarkdown },
  {
    header: 'Analysis Status',
    field: 'analysisStatus',
    format: status => (FAMILY_ANALYSIS_STATUS_OPTIONS.find(option => option.value === status) || {}).name,
  },
  { header: 'Analysed By', field: 'analysedBy', format: analysedBy => analysedBy.map(o => o.user.display_name).join(',') },
  { header: 'Analysis Summary', field: 'analysisSummary', format: stripMarkdown },
  { header: 'Analysis Notes', field: 'analysisNotes', format: stripMarkdown },
]

export const INTERNAL_FAMILY_EXPORT_DATA = [
  { header: 'Internal Case Review Summary', field: 'internalCaseReviewSummary', format: stripMarkdown },
  { header: 'Internal Case Review Notes', field: 'internalCaseReviewNotes', format: stripMarkdown },
]

export const INDIVIDUAL_EXPORT_DATA = [
  { header: 'Family ID', field: 'familyId' },
  { header: 'Individual ID', field: 'individualId' },
  { header: 'Paternal ID', field: 'paternalId' },
  { header: 'Maternal ID', field: 'maternalId' },
  { header: 'Sex', field: 'sex', format: sex => SEX_LOOKUP[sex] },
  { header: 'Affected Status', field: 'affected', format: affected => AFFECTED_LOOKUP[affected] },
  { header: 'Notes', field: 'notes', format: stripMarkdown  },
  {
    header: 'HPO Terms (present)',
    field: 'phenotipsData',
    format: phenotipsData => (
      (phenotipsData || {}).features ?
        phenotipsData.features.filter(feature => feature.observed === 'yes').map(feature => feature.label).join(', ') :
        ''
    ),
  },
  {
    header: 'HPO Terms (absent)',
    field: 'phenotipsData',
    format: phenotipsData => (
      (phenotipsData || {}).features ?
        phenotipsData.features.filter(feature => feature.observed === 'no').map(feature => feature.label).join(', ') :
        ''
    ),
  },
]

export const INTERNAL_INDIVIDUAL_EXPORT_DATA = [
  { header: 'Case Review Status', field: 'caseReviewStatus', format: status => CASE_REVIEW_STATUS_OPT_LOOKUP[status].name },
  { header: 'Case Review Status Last Modified', field: 'caseReviewStatusLastModifiedDate' },
  { header: 'Case Review Status Last Modified By', field: 'caseReviewStatusLastModifiedBy' },
  { header: 'Case Review Discussion', field: 'caseReviewDiscussion', format: stripMarkdown },
]

export const SORT_BY_FAMILY_GUID = 'FAMILY_GUID'
export const SORT_BY_XPOS = 'XPOS'
export const SORT_BY_PATHOGENICITY = 'PATHOGENICITY'
export const SORT_BY_IN_OMIM = 'IN_OMIM'

const clinsigSeverity = (variant) => {
  const clinvarSignificance = variant.clinvar.clinsig && variant.clinvar.clinsig.split('/')[0]
  const hgmdSignificance = variant.hgmd.class
  if (!clinvarSignificance && !hgmdSignificance) return -10
  let clinvarSeverity = 0.1
  if (clinvarSignificance) {
    clinvarSeverity = clinvarSignificance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[clinvarSignificance] + 1 : 0.5
  }
  const hgmdSeverity = hgmdSignificance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[hgmdSignificance] + 0.5 : 0
  return clinvarSeverity + hgmdSeverity
}

export const VARIANT_SORT_OPTONS = [
  { value: SORT_BY_FAMILY_GUID, text: 'Family', comparator: (a, b) => a.familyGuid.localeCompare(b.familyGuid) },
  { value: SORT_BY_XPOS, text: 'Position', comparator: (a, b) => a.xpos - b.xpos },
  { value: SORT_BY_PATHOGENICITY, text: 'Pathogenicity', comparator: (a, b) => clinsigSeverity(b) - clinsigSeverity(a) },
  { value: SORT_BY_IN_OMIM, text: 'In OMIM', comparator: (a, b) => b.genes.some(gene => gene.diseaseDbPheotypes.length > 0) - a.genes.some(gene => gene.diseaseDbPheotypes.length > 0) },
]

export const VARIANT_EXPORT_DATA = [
  { header: 'chrom' },
  { header: 'pos' },
  { header: 'ref' },
  { header: 'alt' },
  { header: 'tags', getVal: variant => variant.tags.map(tag => tag.name).join('|') },
  { header: 'notes', getVal: variant => variant.notes.map(note => `${note.user}: ${note.note}`).join('|') },
  { header: 'family', getVal: variant => variant.familyGuid.split(/_(.+)/)[1] },
  { header: 'gene', getVal: variant => variant.annotation.mainTranscript.symbol },
  { header: 'consequence', getVal: variant => variant.annotation.vepConsequence },
  { header: '1kg_freq', getVal: variant => variant.annotation.freqs.g1k },
  { header: 'exac_freq', getVal: variant => variant.annotation.freqs.exac },
  { header: 'sift', getVal: variant => variant.annotation.sift },
  { header: 'polyphen', getVal: variant => variant.annotation.polyphen },
  { header: 'hgvsc', getVal: variant => variant.annotation.mainTranscript.hgvsc },
  { header: 'hgvsp', getVal: variant => variant.annotation.mainTranscript.hgvsp },
]

export const VARIANT_GENOTYPE_EXPORT_DATA = [
  { header: 'sample_id', getVal: (genotype, individualId) => individualId },
  { header: 'genotype', getVal: genotype => (genotype.alleles.length ? genotype.alleles.join('/') : './.') },
  { header: 'filter' },
  { header: 'ad' },
  { header: 'dp' },
  { header: 'gq' },
  { header: 'ab' },
]

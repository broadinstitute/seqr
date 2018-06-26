/* eslint-disable no-multi-spaces */

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
} from 'shared/utils/constants'

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


export const FAMILY_FILTER_OPTIONS = [
  {
    value: SHOW_ALL,
    name: 'All',
    createFilter: () => () => (true),
  },
  /*
  {
    value: SHOW_DATA_LOADED,
    name: 'Data Loaded',
    createFilter: (familiesByGuid, individualsByGuid, samplesByGuid) => familyGuid =>
      familiesByGuid[familyGuid].individualGuids.filter(
        individualGuid => individualsByGuid[individualGuid].sampleGuids.filter(
          sampleGuid => samplesByGuid[sampleGuid].isLoaded,
        ).length > 0,
      ).length > 0,
  },
   CASE_REVIEW_STATUS_ACCEPTED
  */
  {
    value: SHOW_SOLVED,
    name: 'Solved',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family =>
      SOLVED_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_STRONG_CANDIDATE,
    name: 'Strong Candidate',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family =>
      STRONG_CANDIDATE_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_REVIEWED_NO_CLEAR_CANDIDATE,
    name: 'No Clear Candidate',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family => family.analysisStatus === FAMILY_STATUS_REVIEWED_NO_CLEAR_CANDIDATE,
  },
  {
    value: SHOW_ANALYSIS_IN_PROGRESS,
    name: 'Analysis In Progress',
    internalOmit: true,
    /* eslint-disable no-unused-vars */
    createFilter: families => family =>
      ANALYSIS_IN_PROGRESS_STATUSES.has(family.analysisStatus),
  },
  {
    value: SHOW_ACCEPTED,
    name: 'Accepted',
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED).length > 0,
  },
  {
    value: SHOW_NOT_ACCEPTED,
    name: 'Not Accepted',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_NOT_ACCEPTED).length > 0,
  },
  {
    value: SHOW_IN_REVIEW,
    name: 'In Review',
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_IN_REVIEW).length > 0,
  },
  {
    value: SHOW_UNCERTAIN,
    name: 'Uncertain',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_UNCERTAIN).length > 0,
  },
  {
    value: SHOW_MORE_INFO_NEEDED,
    name: 'More Info Needed',
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED).length > 0,
  },
  {
    value: SHOW_NOT_IN_REVIEW,
    name: 'Not In Review',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_NOT_IN_REVIEW).length > 0,
  },
  {
    value: SHOW_PENDING_RESULTS_AND_RECORDS,
    name: 'Pending Results and Records',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_PENDING_RESULTS_AND_RECORDS).length > 0,
  },
  {
    value: SHOW_WAITLIST,
    name: 'Waitlist',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_WAITLIST).length > 0,
  },
  {
    value: SHOW_WITHDREW,
    name: 'Withdrew',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_WITHDREW).length > 0,
  },
  {
    value: SHOW_INELIGIBLE,
    name: 'Ineligible',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_INELIGIBLE).length > 0,
  },
  {
    value: SHOW_DECLINED_TO_PARTICIPATE,
    name: 'Declined to Participate',
    internalOnly: true,
    createFilter: (families, individuals) => family =>
      individuals.filter(individual =>
        individual.familyGuid === family.familyGuid &&
        individual.caseReviewStatus === CASE_REVIEW_STATUS_DECLINED_TO_PARTICIPATE).length > 0,
  },
]


export const SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
export const SORT_BY_FAMILY_ADDED_DATE = 'FAMILY_ADDED_DATE'
export const SORT_BY_DATA_LOADED_DATE = 'DATA_LOADED_DATE'

export const FAMILY_SORT_OPTIONS = [
  {
    value: SORT_BY_FAMILY_NAME,
    name: 'Family Name',
    /* eslint-disable no-unused-vars */
    createSortKeyGetter: familiesByGuid => family => family.displayName,
  },
  {
    value: SORT_BY_FAMILY_ADDED_DATE,
    name: 'Date Added',
    createSortKeyGetter: (familiesByGuid, individualsByGuid) => family =>
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
    createSortKeyGetter: (familiesByGuid, individualsByGuid, samplesByGuid) => family =>
      family.individualGuids.map(individualGuid => individualsByGuid[individualGuid]).reduce(
        (acc, individual) => {
          const indivLoadedDate = individual.sampleGuids.map(sampleGuid => samplesByGuid[sampleGuid]).reduce(
            (acc2, sample) => {
              const sampleLoadedDate = sample.loadedDate
              return sampleLoadedDate > acc2 ? sampleLoadedDate : acc2
            },
            '2000-01-01T01:00:00.000Z',
          )
          return indivLoadedDate > acc ? indivLoadedDate : acc
        },
        '2000-01-01T01:00:00.000Z',
      ),
  },
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

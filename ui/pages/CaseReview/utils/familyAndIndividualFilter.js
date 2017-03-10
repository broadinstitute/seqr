import {
  CASE_REVIEW_STATUS_ACCEPTED_EXOME,
  CASE_REVIEW_STATUS_ACCEPTED_GENOME,
  CASE_REVIEW_STATUS_ACCEPTED_RNASEQ,
  CASE_REVIEW_STATUS_UNCERTAIN_KEY,
  CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY,
  CASE_REVIEW_STATUS_HOLD_KEY,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY,
  CASE_REVIEW_STATUS_IN_REVIEW_KEY,
  CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY,

  SHOW_ALL,
  SHOW_ACCEPTED,
  SHOW_NOT_ACCEPTED,
  SHOW_IN_REVIEW,
  SHOW_UNCERTAIN,
  SHOW_MORE_INFO_NEEDED,
  SHOW_HOLD,
} from '../constants'


/**
 * Returns an object that maps each family filter drop-down option (CaseReviewTable.SHOW_*)
 * to the set of individual case review statuses (Individual.CASE_REVIEW_STATUS_*) that should
 * be shown when the user selects that particular filter.
 */
export const getFamilyToIndividualFilterMap = () => {
  return {
    [SHOW_ACCEPTED]: [
      CASE_REVIEW_STATUS_ACCEPTED_EXOME,
      CASE_REVIEW_STATUS_ACCEPTED_GENOME,
      CASE_REVIEW_STATUS_ACCEPTED_RNASEQ,
      CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY,
    ],
    [SHOW_NOT_ACCEPTED]: [
      CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY,
    ],
    [SHOW_IN_REVIEW]: [
      CASE_REVIEW_STATUS_IN_REVIEW_KEY,
    ],
    [SHOW_UNCERTAIN]: [
      CASE_REVIEW_STATUS_UNCERTAIN_KEY,
      CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY,
    ],
    [SHOW_HOLD]: [
      CASE_REVIEW_STATUS_HOLD_KEY,
    ],
    [SHOW_MORE_INFO_NEEDED]: [
      CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY,
    ],
  }
}

/**
 * Returns a function which returns true if a given individual's caseReviewStatus is one of the
 * setOfStatusesToKeep.
 * @param individualsByGuid {object} maps each GUID to an object describing that individual.
 * @param setOfStatusesToKeep {Set} one or more Individual.CASE_REVIEW_STATUS_* constants.
 * @returns {function}
 */
export const createIndividualFilter = (individualsByGuid, setOfStatusesToKeep) => {
  /* Returns a function to filter individuals by caseReviewStatus */
  return (individualGuid) => {
    return setOfStatusesToKeep.has(individualsByGuid[individualGuid].caseReviewStatus)
  }
}

/**
 * Returns a function that returns true if a given family contains at least one individual that
 * passes the given familiesFilter.
 * @param familiesFilter {string} one of the SHOW_* constants
 * @param familyGuidToIndivGuids {object}
 * @param individualsByGuid {object}
 * @returns {function}
 */
export const createFamilyFilter = (familiesFilter, familyGuidToIndivGuids, individualsByGuid) => {
  const individualsFilter = createIndividualFilter(
    individualsByGuid,
    new Set(getFamilyToIndividualFilterMap()[familiesFilter]),
  )

  //return true if at least 1 individual in the family has the matching caseReviewStatus
  return (familyGuid) => {
    if (familiesFilter === SHOW_ALL) {
      return true
    }
    return familyGuidToIndivGuids[familyGuid].filter(individualsFilter).length > 0
  }
}

/* eslint-disable array-callback-return */

import { createSelector } from 'reselect'

import { CASE_REVIEW_STATUS_OPTIONS } from 'shared/constants/caseReviewConstants'
import { getIndividualsByGuid } from 'shared/utils/redux/commonDataActionsAndSelectors'


/**
 * function that returns a dictionary that maps each case review status to a count of
 * Individuals with that status.
 *
 * @param state {object} global Redux state
 */
export const getCaseReviewStatusCounts = createSelector(
  getIndividualsByGuid,
  (individualsByGuid) => {
    const caseReviewStatusCounts = Object.values(individualsByGuid).reduce((acc, individual) => ({
      ...acc, [individual.caseReviewStatus]: (acc[individual.caseReviewStatus] || 0) + 1,
    }), {})

    return CASE_REVIEW_STATUS_OPTIONS.map(option => (
      { ...option, count: (caseReviewStatusCounts[option.value] || 0) }),
    )
  })

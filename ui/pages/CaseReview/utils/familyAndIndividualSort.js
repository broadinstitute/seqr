import max from 'lodash/max'

import { genericComparator } from 'shared/utils/sortUtils'
import { SORT_BY_FAMILY_NAME, SORT_BY_DATE_ADDED, SORT_BY_DATE_LAST_CHANGED } from '../constants'

/**
 * Returns a comparator function for sorting families according to one of the SORT_BY_* constants.
 * @params familiesSortOrder {string}
 * @params direction {number}
 * @param familiesByGuid {object}
 * @returns {function(*, *): number}
 */
export const createFamilySortComparator = (familiesSortOrder, direction, familiesByGuid, familyGuidToIndivGuids, individualsByGuid) => {
  switch (familiesSortOrder) {
    case SORT_BY_FAMILY_NAME:
      return (a, b) => {
        return -1 * direction * genericComparator(familiesByGuid[a].displayName, familiesByGuid[b].displayName)
      }
    case SORT_BY_DATE_ADDED:
      return (a, b) => {
        a = max(familyGuidToIndivGuids[a].map(i => individualsByGuid[i].createdDate || '2000-01-01T01:00:00.000Z'))
        b = max(familyGuidToIndivGuids[b].map(i => individualsByGuid[i].createdDate || '2000-01-01T01:00:00.000Z'))
        return direction * genericComparator(a, b)
      }
    case SORT_BY_DATE_LAST_CHANGED:
      return (a, b) => {
        a = max(familyGuidToIndivGuids[a].map(i => individualsByGuid[i].caseReviewStatusLastModifiedDate || '2000-01-01T01:00:00.000Z'))
        b = max(familyGuidToIndivGuids[b].map(i => individualsByGuid[i].caseReviewStatusLastModifiedDate || '2000-01-01T01:00:00.000Z'))

        return direction * genericComparator(a, b)
      }
    default:
      return (a, b) => {
        return direction * genericComparator(a, b)
      }
  }
}

/**
 * In the CaseReview table, Indivdiuals will be sorted according to affected status in this order.
 */
const AFFECTED_STATUS_ORDER = {
  A: 1,
  N: 2,
  U: 3, //unknown
}

/**
 * Returns a comparator function for sorting individuals by their 'affected' status.
 * @param individualsByGuid {object}
 * @returns {function(*, *): number}
 */
export const createIndividualSortComparator = (individualsByGuid) => {
  return (a, b) => {
    return -1 * genericComparator(
      AFFECTED_STATUS_ORDER[individualsByGuid[a].affected],
      AFFECTED_STATUS_ORDER[individualsByGuid[b].affected],
    )
  }
}

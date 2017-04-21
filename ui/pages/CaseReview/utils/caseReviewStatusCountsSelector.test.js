/* eslint-disable no-undef */

import orderBy from 'lodash/orderBy'
import { getCaseReviewStatusCounts } from './caseReviewStatusCountsSelector'
import { STATE1 } from '../fixtures'

test('getCaseReviewStatusCounts', () => {
  const caseReviewStatusCounts = getCaseReviewStatusCounts(STATE1)
  const caseReviewStatusCountsSorted = orderBy(caseReviewStatusCounts, [obj => obj.count], 'desc')

  expect(caseReviewStatusCountsSorted.length).toEqual(9)

  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('name', 'In Review')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('value', 'I')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('count', 2)

  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('name', 'Accepted: Exome')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('value', 'E')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('count', 1)

  expect(caseReviewStatusCountsSorted[2]).toHaveProperty('count', 0)
})

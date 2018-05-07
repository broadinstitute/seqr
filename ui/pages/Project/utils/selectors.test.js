/* eslint-disable no-undef */

import orderBy from 'lodash/orderBy'
import { getVisibleFamilies, getVisibleFamiliesInSortedOrder, getVisibleSortedFamiliesWithIndividuals, getCaseReviewStatusCounts } from './selectors'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

test('getVisibleFamilies', () => {
  const visibleFamilies = getVisibleFamilies(STATE_WITH_2_FAMILIES)

  expect(visibleFamilies.length).toEqual(2)
  expect(visibleFamilies[0].familyGuid).toEqual('F011652_1')
  expect(visibleFamilies[1].familyGuid).toEqual('F011652_2')
})

test('getVisibleFamiliesInSortedOrder', () => {
  const visibleFamiliesSorted = getVisibleFamiliesInSortedOrder(STATE_WITH_2_FAMILIES)

  expect(visibleFamiliesSorted.length).toEqual(2)
  expect(visibleFamiliesSorted[0].familyGuid).toEqual('F011652_2')
  expect(visibleFamiliesSorted[1].familyGuid).toEqual('F011652_1')
})

test('getVisibleSortedFamiliesWithIndividuals', () => {
  const visibleSortedFamiliesWithIndividuals = getVisibleSortedFamiliesWithIndividuals(STATE_WITH_2_FAMILIES)
  expect(visibleSortedFamiliesWithIndividuals.length).toEqual(2)
  expect(visibleSortedFamiliesWithIndividuals[0].individuals.length).toEqual(3)
  expect(visibleSortedFamiliesWithIndividuals[1].individuals.length).toEqual(3)
})

test('getCaseReviewStatusCounts', () => {
  const caseReviewStatusCounts = getCaseReviewStatusCounts(STATE_WITH_2_FAMILIES)
  const caseReviewStatusCountsSorted = orderBy(caseReviewStatusCounts, [obj => obj.count], 'desc')

  expect(caseReviewStatusCountsSorted.length).toEqual(11)

  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('name', 'In Review')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('value', 'I')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('count', 4)


  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('name', 'Accepted')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('value', 'A')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('count', 2)

  expect(caseReviewStatusCountsSorted[2]).toHaveProperty('count', 0)
})
/* eslint-disable no-undef */

import { getVisibleFamilyGuids, getVisibleFamiliesInSortedOrder, getFamilyGuidToIndividuals } from './visibleFamiliesSelector'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

test('getVisibleFamilyGuids', () => {
  const visibleFamilyGuids = getVisibleFamilyGuids(STATE_WITH_2_FAMILIES)

  expect(visibleFamilyGuids).toEqual(['F011652_1', 'F011652_2'])
})

test('getVisibleFamiliesInSortedOrder', () => {
  const visibleFamiliesSorted = getVisibleFamiliesInSortedOrder(STATE_WITH_2_FAMILIES)

  expect(visibleFamiliesSorted.length).toEqual(2)
  expect(visibleFamiliesSorted[0].familyGuid).toEqual('F011652_2')
  expect(visibleFamiliesSorted[1].familyGuid).toEqual('F011652_1')
})

test('getFamilyGuidToIndividuals', () => {
  const familyGuidToIndividuals = getFamilyGuidToIndividuals(STATE_WITH_2_FAMILIES)
  expect(Object.keys(familyGuidToIndividuals).length).toEqual(2)
  expect(familyGuidToIndividuals.F011652_1.length).toEqual(3)
  expect(familyGuidToIndividuals.F011652_2.length).toEqual(3)
})


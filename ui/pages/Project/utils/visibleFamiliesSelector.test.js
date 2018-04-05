/* eslint-disable no-undef */

import { getVisibleFamilies, getVisibleFamiliesInSortedOrder, getVisibleSortedFamiliesWithIndividuals } from './visibleFamiliesSelector'

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


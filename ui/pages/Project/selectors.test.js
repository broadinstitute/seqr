/* eslint-disable no-undef */

import orderBy from 'lodash/orderBy'
import { getVisibleFamilies, getVisibleFamiliesInSortedOrder, getVisibleSortedFamiliesWithIndividuals,
  getCaseReviewStatusCounts, getProjectSavedVariants, getFilteredProjectSavedVariants,
  getVisibleSortedProjectSavedVariants, getProjectAnalysisGroupFamiliesByGuid } from './selectors'

import { STATE_WITH_2_FAMILIES } from './fixtures'

test('getVisibleFamilies', () => {

  const visibleFamilies = getVisibleFamilies.resultFunc(
    STATE_WITH_2_FAMILIES.familiesByGuid, STATE_WITH_2_FAMILIES.individualsByGuid, STATE_WITH_2_FAMILIES.samplesByGuid,
    STATE_WITH_2_FAMILIES.user, STATE_WITH_2_FAMILIES.familyTableState.familiesFilter,
    Object.keys(STATE_WITH_2_FAMILIES.familiesByGuid)
  )

  expect(visibleFamilies.length).toEqual(2)
  expect(visibleFamilies[0].familyGuid).toEqual('F011652_1')
  expect(visibleFamilies[1].familyGuid).toEqual('F011652_2')
})

test('getVisibleFamiliesInSortedOrder', () => {
  const visibleFamiliesSorted = getVisibleFamiliesInSortedOrder.resultFunc(
    Object.values(STATE_WITH_2_FAMILIES.familiesByGuid), STATE_WITH_2_FAMILIES.individualsByGuid,
    STATE_WITH_2_FAMILIES.samplesByGuid, STATE_WITH_2_FAMILIES.familyTableState.familiesSortOrder,
    STATE_WITH_2_FAMILIES.familyTableState.familiesSortDirection)

  expect(visibleFamiliesSorted.length).toEqual(2)
  expect(visibleFamiliesSorted[0].familyGuid).toEqual('F011652_2')
  expect(visibleFamiliesSorted[1].familyGuid).toEqual('F011652_1')
})

test('getVisibleSortedFamiliesWithIndividuals', () => {
  const visibleSortedFamiliesWithIndividuals = getVisibleSortedFamiliesWithIndividuals.resultFunc(
    Object.values(STATE_WITH_2_FAMILIES.familiesByGuid), STATE_WITH_2_FAMILIES.individualsByGuid,
    STATE_WITH_2_FAMILIES.samplesByGuid,
  )
  expect(visibleSortedFamiliesWithIndividuals.length).toEqual(2)
  expect(visibleSortedFamiliesWithIndividuals[0].individuals.length).toEqual(3)
  expect(visibleSortedFamiliesWithIndividuals[1].individuals.length).toEqual(3)
  expect(visibleSortedFamiliesWithIndividuals[0].firstSample).toEqual(null)
  expect(visibleSortedFamiliesWithIndividuals[1].firstSample.sampleGuid).toEqual('S2310656_wal_mc16200_mc16203')
})

test('getCaseReviewStatusCounts', () => {
  const caseReviewStatusCounts = getCaseReviewStatusCounts(STATE_WITH_2_FAMILIES)
  const caseReviewStatusCountsSorted = orderBy(caseReviewStatusCounts, [obj => obj.count], 'desc')

  expect(caseReviewStatusCountsSorted.length).toEqual(7)

  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('name', 'In Review')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('value', 'I')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('count', 4)


  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('name', 'Accepted')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('value', 'A')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('count', 2)

  expect(caseReviewStatusCountsSorted[2]).toHaveProperty('count', 0)

})

test('getProjectSavedVariants', () => {
  expect(getProjectSavedVariants(STATE_WITH_2_FAMILIES, { match: { params:  {} } }).length).toEqual(3)

  const savedReviewVariants = getProjectSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { tag: 'Review' } } }
  )
  expect(savedReviewVariants.length).toEqual(2)
  expect(savedReviewVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedReviewVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')

  const savedFamilyVariants = getProjectSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { familyGuid: 'F011652_1' } } }
  )
  expect(savedFamilyVariants.length).toEqual(2)
  expect(savedFamilyVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedFamilyVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')

  const savedVariants= getProjectSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { variantGuid: 'SV0000004_116042722_r0390_1000' } } }
  )
  expect(savedVariants.length).toEqual(1)
  expect(savedFamilyVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
})

test('getFilteredProjectSavedVariants', () => {
  const savedVariants = getFilteredProjectSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  {} } }
  )
  expect(savedVariants.length).toEqual(2)
  expect(savedVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')
})

test('getVisibleSortedProjectSavedVariants', () => {
  const savedVariants = getVisibleSortedProjectSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  {} } }
  )
  expect(savedVariants.length).toEqual(1)
  expect(savedVariants[0].variantId).toEqual('SV0000002_1248367227_r0390_100')
})

test('getProjectAnalysisGroupFamiliesByGuid', () => {

  const families = getProjectAnalysisGroupFamiliesByGuid.resultFunc(
    STATE_WITH_2_FAMILIES.familiesByGuid, STATE_WITH_2_FAMILIES.analysisGroupsByGuid, 'AG0000183_test_group',
  )

  expect(Object.keys(families)).toEqual(['F011652_1'])
  expect(families.F011652_1.familyId).toEqual('1')
})

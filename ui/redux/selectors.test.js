/* eslint-disable no-undef */

import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'
import { getSelectedSavedVariants, getFilteredSavedVariants, getVisibleSortedSavedVariants } from './selectors'

test('getSelectedSavedVariants', () => {

  expect(getSelectedSavedVariants(STATE_WITH_2_FAMILIES, { match: { params:  {} } }).length).toEqual(3)

  const savedReviewVariants = getSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { tag: 'Review' } } }
  )
  expect(savedReviewVariants.length).toEqual(2)
  expect(savedReviewVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedReviewVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')

  const savedNotesVariants = getSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { tag: 'Has Notes' } } }
  )
  expect(savedNotesVariants.length).toEqual(1)
  expect(savedNotesVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')


  const savedFamilyVariants = getSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { familyGuid: 'F011652_1' } } }
  )
  expect(savedFamilyVariants.length).toEqual(2)
  expect(savedFamilyVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedFamilyVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')

  const savedAnalysisGroupVariants = getSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { analysisGroupGuid: 'AG0000183_test_group' } } }
  )
  expect(savedAnalysisGroupVariants.length).toEqual(2)
  expect(savedAnalysisGroupVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedAnalysisGroupVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')


  const savedVariants= getSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { variantGuid: 'SV0000004_116042722_r0390_1000' } } }
  )
  expect(savedVariants.length).toEqual(1)
  expect(savedFamilyVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
})

test('getFilteredSavedVariants', () => {
  const savedVariants = getFilteredSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  {} } }
  )
  expect(savedVariants.length).toEqual(2)
  expect(savedVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')
})

test('getVisibleSortedSavedVariants', () => {
  const savedVariants = getVisibleSortedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  {} } }
  )
  expect(savedVariants.length).toEqual(1)
  expect(savedVariants[0].variantId).toEqual('SV0000002_1248367227_r0390_100')
})

/* eslint-disable no-undef */

import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'
import {
  getPairedSelectedSavedVariants,
  getVisibleSortedSavedVariants,
  getPairedFilteredSavedVariants,
  getVariantTagNotesByGuid,
} from './selectors'

test('getPairedSelectedSavedVariants', () => {

  const savedAllVariants = getPairedSelectedSavedVariants(STATE_WITH_2_FAMILIES, { match: { params:  {} } })
  expect(savedAllVariants.length).toEqual(3)
  expect(savedAllVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedAllVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')
  expect(savedAllVariants[2].length).toEqual(2)
  expect(savedAllVariants[2][0].variantId).toEqual('SV0000003_2246859832_r0390_100')
  expect(savedAllVariants[2][1].variantId).toEqual('SV0000005_2246859833_r0390_100')

  const savedReviewVariants = getPairedSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { tag: 'Review' } } }
  )
  expect(savedReviewVariants.length).toEqual(2)
  expect(savedReviewVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedReviewVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')

  const savedNotesVariants = getPairedSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { tag: 'Has Notes' } } }
  )
  expect(savedNotesVariants.length).toEqual(1)
  expect(savedNotesVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')


  const savedFamilyVariants = getPairedSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { familyGuid: 'F011652_1' } } }
  )
  expect(savedFamilyVariants.length).toEqual(2)
  expect(savedFamilyVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedFamilyVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')

  const savedAnalysisGroupVariants = getPairedSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { analysisGroupGuid: 'AG0000183_test_group' } } }
  )
  expect(savedAnalysisGroupVariants.length).toEqual(2)
  expect(savedAnalysisGroupVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(savedAnalysisGroupVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')


  const savedVariants = getPairedSelectedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  { variantGuid: 'SV0000004_116042722_r0390_1000' } } }
  )
  expect(savedVariants.length).toEqual(1)
  expect(savedFamilyVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
})

test('getVariantTagNotesByGuid', () => {
  const tagsNotesByGuid = getVariantTagNotesByGuid(
    STATE_WITH_2_FAMILIES,
  )
  expect(Object.keys(tagsNotesByGuid).length).toEqual(5)
  expect(tagsNotesByGuid.SV0000004_116042722_r0390_1000.notes.length).toEqual(1)
  expect(tagsNotesByGuid.SV0000004_116042722_r0390_1000.tags.length).toEqual(1)
  expect(tagsNotesByGuid.SV0000002_1248367227_r0390_100.tags.length).toEqual(2)
  expect(tagsNotesByGuid.SV0000003_2246859832_r0390_100).toEqual({ variantGuids: 'SV0000003_2246859832_r0390_100'})
  expect(tagsNotesByGuid.SV0000005_2246859833_r0390_100).toEqual({ variantGuids: 'SV0000005_2246859833_r0390_100'})
  expect(tagsNotesByGuid['SV0000003_2246859832_r0390_100,SV0000005_2246859833_r0390_100'].tags.length).toEqual(1)
})

test('getPairedFilteredSavedVariants', () => {
  const pairedSavedVariants = getPairedFilteredSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  {} } }
  )
  expect(pairedSavedVariants.length).toEqual(2)
  expect(pairedSavedVariants[0].variantId).toEqual('SV0000004_116042722_r0390_1000')
  expect(pairedSavedVariants[1].variantId).toEqual('SV0000002_1248367227_r0390_100')
})

test('getVisibleSortedSavedVariants', () => {
  const savedVariants = getVisibleSortedSavedVariants(
    STATE_WITH_2_FAMILIES, { match: { params:  {} } }
  )
  expect(savedVariants.length).toEqual(1)
  expect(savedVariants[0].variantId).toEqual('SV0000002_1248367227_r0390_100')
})


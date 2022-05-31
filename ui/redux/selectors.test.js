/* eslint-disable no-undef */

import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'
import {
  getVariantTagNotesByFamilyVariants,
  getSearchGeneBreakdownValues,
  getTagTypesByProject,
  getUserOptions,
} from './selectors'
import {FAMILY_GUID, GENE_ID, SEARCH, SEARCH_HASH, STATE} from "../pages/Search/fixtures";

test('getVariantTagNotesByByFamilyVariants', () => {
  const tagsNotesByGuid = getVariantTagNotesByFamilyVariants(
    STATE_WITH_2_FAMILIES,
  )
  expect(Object.keys(tagsNotesByGuid).length).toEqual(2)
  expect(Object.keys(tagsNotesByGuid.F011652_1).length).toEqual(3)
  expect(tagsNotesByGuid.F011652_1['22-45919065-TTTC-T'].notes.length).toEqual(1)
  expect(tagsNotesByGuid.F011652_1['22-45919065-TTTC-T'].tags.length).toEqual(1)
  expect(tagsNotesByGuid.F011652_1['1-248367227-TC-T'].tags.length).toEqual(2)
  expect(tagsNotesByGuid.F011652_1['batch_123_DEL'].tags).toEqual(undefined)
  expect(Object.keys(tagsNotesByGuid.F011652_2).length).toEqual(3)
  expect(tagsNotesByGuid.F011652_2['22-248367227-C-T']).toEqual({ variantGuids: 'SV0000003_2246859832_r0390_100'})
  expect(tagsNotesByGuid.F011652_2['22-248367228-C-T']).toEqual({ variantGuids: 'SV0000005_2246859833_r0390_100'})
  expect(tagsNotesByGuid.F011652_2['22-248367227-C-T,22-248367228-C-T'].tags.length).toEqual(1)
})

test('getSearchGeneBreakdownValues', () => {
  expect(getSearchGeneBreakdownValues(STATE, { searchHash: SEARCH_HASH })).toEqual([{
    numVariants: 3,
    numFamilies: 1,
    families: [{ family: STATE.familiesByGuid[FAMILY_GUID], count: 2 }],
    search: SEARCH.search,
    geneId: GENE_ID,
    geneSymbol: 'OR2M3',
  }])
})

test('getTagTypesByProject', () => {
  expect(getTagTypesByProject(STATE, {})).toEqual(
    { R0237_1000_genomes_demo: [] },
  )
})

test('getUserOptions', () => {
  const options = getUserOptions(STATE_WITH_2_FAMILIES)
  expect(Object.keys(options).length).toEqual(7)
  expect(options[1]).toEqual({ key: '4MW8vPtmHG', value: '4MW8vPtmHG', text: 'Mekdes (mgetaneh@broadinstitute.org)'})
})

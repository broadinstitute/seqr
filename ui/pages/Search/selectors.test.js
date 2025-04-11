import { getProjectDatasetTypes } from 'redux/selectors'
import { getIntitialSearch, getLocusListOptions, getDatasetTypes, getSearchGeneBreakdownValues } from './selectors'

import {
  STATE,
  SEARCH_HASH,
  SEARCH,
  PROJECT_GUID,
  FAMILY_GUID,
  ANALYSIS_GROUP_GUID,
  DYNAMIC_ANALYSIS_GROUP_GUID,
  LOCUS_LIST,
  GENE_ID
} from './fixtures'

const NO_SEARCH_STATE = { ...STATE, currentSearchHash: null }
const EXPECTED_INITAL_SEARCH = { projectFamilies: [{ projectGuid: PROJECT_GUID, familyGuids: [FAMILY_GUID] }] }

test('getIntitialSearch', () => {

  expect(getIntitialSearch(NO_SEARCH_STATE, { match: { params: {} } })).toEqual(null)

  expect(getIntitialSearch(STATE, { match: { params: { searchHash: SEARCH_HASH } } })).toEqual(SEARCH)

  expect(getIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { projectGuid: PROJECT_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getIntitialSearch(NO_SEARCH_STATE, { match: { params: { projectGuid: 'foo' } } })).toEqual(
    { projectFamilies: [{ projectGuid: 'foo', familyGuids: null }] }
  )

  expect(getIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { familyGuid: FAMILY_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getIntitialSearch(NO_SEARCH_STATE, { match: { params: { familyGuid: 'foo' } } })).toEqual(
    { projectFamilies: [{ familyGuids: ['foo'] }] }
  )

  expect(getIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { projectGuid: PROJECT_GUID, analysisGroupGuid: ANALYSIS_GROUP_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getIntitialSearch(NO_SEARCH_STATE, { match: { params: { analysisGroupGuid: 'foo' } } })).toEqual(
    { projectFamilies: [{ analysisGroupGuid: 'foo' }] }
  )

  expect(getIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { projectGuid: PROJECT_GUID, analysisGroupGuid: DYNAMIC_ANALYSIS_GROUP_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
})

test('getLocusListOptions', () => {
  expect(getLocusListOptions(
    STATE, { projectFamilies: [{ projectGuid: PROJECT_GUID }] },
  )).toEqual([{
    text: LOCUS_LIST.name,
    value: LOCUS_LIST.locusListGuid,
    key: LOCUS_LIST.locusListGuid,
    description: '60 Genes',
    icon: { name: 'users', size: 'small' },
    category: 'Project Lists',
    categoryRank: 0,
  }])
})

test('getDatasetTypes', () => {
  expect(getDatasetTypes(STATE, { projectFamilies: [{ projectGuid: PROJECT_GUID }] })).toEqual('SNV_INDEL,SV')
  expect(getDatasetTypes(STATE, EXPECTED_INITAL_SEARCH)).toEqual('SNV_INDEL')
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

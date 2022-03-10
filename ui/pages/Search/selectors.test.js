import { getProjectDatasetTypes } from 'redux/selectors'
import { getIntitialSearch, getSearchedProjectsLocusListOptions, getDatasetTypes } from './selectors'

import { STATE, SEARCH_HASH, SEARCH, PROJECT_GUID, FAMILY_GUID, ANALYSIS_GROUP_GUID, LOCUS_LIST } from './fixtures'

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
    NO_SEARCH_STATE, { match: { params: { analysisGroupGuid: ANALYSIS_GROUP_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getIntitialSearch(NO_SEARCH_STATE, { match: { params: { analysisGroupGuid: 'foo' } } })).toEqual(
    { projectFamilies: [{ analysisGroupGuid: 'foo' }] }
  )
})

test('getSearchedProjectsLocusListOptions', () => {
  expect(getSearchedProjectsLocusListOptions(
    STATE, { projectFamilies: [{ projectGuid: PROJECT_GUID }] },
  )).toEqual([{ value: null }, { text: LOCUS_LIST.name, value: LOCUS_LIST.locusListGuid, key: LOCUS_LIST.locusListGuid }])
})

test('getDatasetTypes', () => {
  expect(getDatasetTypes(STATE, { projectFamilies: [{ projectGuid: PROJECT_GUID }] })).toEqual('SV,VARIANTS')
})

import { getLoadedIntitialSearch, getSearchedProjectsLocusLists } from './selectors'

import { STATE, SEARCH_HASH, SEARCH, PROJECT_GUID, FAMILY_GUID, ANALYSIS_GROUP_GUID, LOCUS_LIST } from './fixtures'

const NO_SEARCH_STATE = { ...STATE, currentSearchHash: null }
const EXPECTED_INITAL_SEARCH = { projectFamilies: [{ projectGuid: PROJECT_GUID, familyGuids: [FAMILY_GUID] }] }

test('getLoadedIntitialSearch', () => {

  expect(getLoadedIntitialSearch(NO_SEARCH_STATE, { match: { params: {} } })).toEqual(null)

  expect(getLoadedIntitialSearch(STATE, { match: { params: { searchHash: SEARCH_HASH } } })).toEqual(SEARCH)
  expect(getLoadedIntitialSearch(
    {
      ...STATE,
      searchesByHash: { [SEARCH_HASH]: { projectFamilies: [...SEARCH.projectFamilies, { projectGuid: 'foo' }] } },
    },
    { match: { params: { searchHash: SEARCH_HASH } } },
  )).toEqual(null)

  expect(getLoadedIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { projectGuid: PROJECT_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getLoadedIntitialSearch(NO_SEARCH_STATE, { match: { params: { projectGuid: 'foo' } } })).toEqual(null)

  expect(getLoadedIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { familyGuid: FAMILY_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getLoadedIntitialSearch(NO_SEARCH_STATE, { match: { params: { familyGuid: 'foo' } } })).toEqual(null)

  expect(getLoadedIntitialSearch(
    NO_SEARCH_STATE, { match: { params: { analysisGroupGuid: ANALYSIS_GROUP_GUID } } })
  ).toEqual(EXPECTED_INITAL_SEARCH)
  expect(getLoadedIntitialSearch(NO_SEARCH_STATE, { match: { params: { analysisGroupGuid: 'foo' } } })).toEqual(null)
})

test('getSearchedProjectsLocusLists', () => {
  expect(getSearchedProjectsLocusLists.resultFunc(
    EXPECTED_INITAL_SEARCH.projectFamilies, STATE.projectsByGuid, STATE.locusListsByGuid,
  )).toEqual([LOCUS_LIST])
})
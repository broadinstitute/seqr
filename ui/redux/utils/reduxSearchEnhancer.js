import { reduxSearch, SearchApi, createSearchAction, getSearchSelectors } from 'redux-search'

const searchApi = new SearchApi()

const resourceSelector = (resourceName, state) => state[resourceName]

const resourceIndexes = {
  familiesByGuid: ({ resources, indexDocument, state }) => {
    Object.values(resources).forEach((family) => {
      indexDocument(family.familyGuid, family.displayName)
      indexDocument(family.familyGuid, family.familyId)
      indexDocument(
        family.familyGuid,
        family.individualGuids.map(individualGuid =>
          ((state.individualsByGuid[individualGuid].phenotipsData || {}).features || []).map(feature => feature.label).join(';'),
        ).join('\n'),
      )
    })
  },
}

// redux-search supports auto-indexing on state change, however this a) is not very preformat and b) does not
// work with an initial search text. Therefore, we should always manually trigger indexing before search
export const indexAndSearch = resourceName => searchText => (dispatch, getState) => {
  const state = getState()
  searchApi.indexResource({
    fieldNamesOrIndexFunction: resourceIndexes[resourceName],
    resources: resourceSelector(resourceName, state),
    resourceName,
    state,
  })
  dispatch(createSearchAction(resourceName)(searchText))
}

export const getSearchResults = resourceName => getSearchSelectors({ resourceName, resourceSelector }).result

export default reduxSearch({ resourceIndexes, searchApi })

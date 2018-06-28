import { reduxSearch, SearchApi, createSearchAction, getSearchSelectors } from 'redux-search'
import { createSelectorCreator, defaultMemoize } from 'reselect'

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

// redux-search result selector always returns new array objects, but as long as the arrays have the same ordered values
// reselect should not update the cached value
const createSortedArraySelector = createSelectorCreator(
  defaultMemoize,
  (arr1, arr2) => arr1.join(',') === arr2.join(','),
)

export const getSearchResults = (resourceName) => {
  const { result } = getSearchSelectors({ resourceName, resourceSelector })
  return createSortedArraySelector(result, results => results)
}

export default reduxSearch({ resourceIndexes, searchApi })

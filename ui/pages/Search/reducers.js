import { combineReducers } from 'redux'

import { updateEntity, RECEIVE_DATA } from 'redux/rootReducer'
import { loadingReducer, createSingleObjectReducer, createSingleValueReducer, createObjectsByIdReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper, getUrlQueryString } from 'shared/utils/httpRequestHelper'
import { SORT_BY_XPOS } from 'shared/utils/constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const UPDATE_CURRENT_SEARCH = 'UPDATE_CURRENT_SEARCH'
const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'
const UPDATE_SEARCHED_VARIANT_DISPLAY = 'UPDATE_SEARCHED_VARIANT_DISPLAY'
const REQUEST_SAVED_SEARCHES = 'REQUEST_SAVED_SEARCHES'
const RECEIVE_SAVED_SEARCHES = 'RECEIVE_SAVED_SEARCHES'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'

// actions

export const loadProjectFamiliesContext = ({ projectGuid, familyGuid, analysisGroupGuid, searchHash }) => {
  return (dispatch, getState) => {
    const state = getState()
    const contextParams = {}
    if (projectGuid && !(state.projectsByGuid[projectGuid] && state.projectsByGuid[projectGuid].variantTagTypes)) {
      contextParams.projectGuid = projectGuid
    }
    else if (familyGuid && !state.familiesByGuid[familyGuid]) {
      contextParams.familyGuid = familyGuid
    }
    else if (analysisGroupGuid && !state.analysisGroupsByGuid[analysisGroupGuid]) {
      contextParams.analysisGroupGuid = analysisGroupGuid
    }
    else if (searchHash) {
      const { projectFamilies } = getState().searchesByHash[searchHash] || {}
      if (projectFamilies && projectFamilies.length) {
        // TODO handle multiple project search
        const project = state.projectsByGuid[projectFamilies[0].projectGuid]
        if (!(project && project.variantTagTypes)) {
          contextParams.projectGuid = projectFamilies[0].projectGuid
        }
      } else {
        contextParams.searchHash = searchHash
      }
    }

    if (Object.keys(contextParams).length) {
      dispatch({ type: REQUEST_PROJECT_DETAILS })
      new HttpRequestHelper('/api/search_context',
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: responseJson })
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).get(contextParams)
    }
  }
}

export const saveHashedSearch = (searchHash, search) => {
  return (dispatch) => {
    dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: { searchesByHash: { [searchHash]: search } } })
  }
}

export const saveSearch = search => updateEntity(search, RECEIVE_SAVED_SEARCHES, '/api/saved_search')

export const loadSearchedVariants = ({ searchHash, variantId, familyGuid, displayUpdates, queryParams, updateQueryParams }) => {
  return (dispatch, getState) => {
    dispatch({ type: REQUEST_SEARCHED_VARIANTS })

    const state = getState()

    const apiQueryParams = {}
    if (searchHash) {
      dispatch({ type: UPDATE_CURRENT_SEARCH, newValue: searchHash })

      let { sort, page } = displayUpdates || queryParams
      if (!page) {
        page = 1
      }
      if (!sort) {
        sort = state.variantSearchDisplay.sort || SORT_BY_XPOS
      }

      apiQueryParams.sort = sort.toLowerCase()
      apiQueryParams.page = page || 1

      // Update search table state and query params
      dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates: { sort: sort.toUpperCase(), page } })
      updateQueryParams(apiQueryParams)
    } else {
      apiQueryParams.familyGuid = familyGuid
    }

    const url = `/api/search/${searchHash || `variant/${variantId}`}?${getUrlQueryString(apiQueryParams)}`
    const search = state.searchesByHash[searchHash]

    // Fetch variants
    new HttpRequestHelper(url,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: responseJson.searchedVariants })
        dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: { searchesByHash: { [searchHash]: responseJson.search } } })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, error: e.message, newValue: [] })
      },
    ).post(search)
  }
}

export const unloadSearchResults = () => {
  return (dispatch) => {
    dispatch({ type: UPDATE_CURRENT_SEARCH, newValue: null })
    dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: [] })
  }
}

export const loadSavedSearches = () => {
  return (dispatch, getState) => {
    if (!Object.keys(getState().savedSearchesByGuid || {}).length) {
      dispatch({ type: REQUEST_SAVED_SEARCHES })

      new HttpRequestHelper('/api/saved_search/all',
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_SAVED_SEARCHES, error: e.message, updatesById: {} })
        },
      ).get()
    }
  }
}


// reducers

export const reducers = {
  currentSearchHash: createSingleValueReducer(UPDATE_CURRENT_SEARCH, null),
  searchedVariants: createSingleValueReducer(RECEIVE_SEARCHED_VARIANTS, []),
  searchedVariantsLoading: loadingReducer(REQUEST_SEARCHED_VARIANTS, RECEIVE_SEARCHED_VARIANTS),
  searchesByHash: createObjectsByIdReducer(RECEIVE_SAVED_SEARCHES, 'searchesByHash'),
  savedSearchesByGuid: createObjectsByIdReducer(RECEIVE_SAVED_SEARCHES, 'savedSearchesByGuid'),
  savedSearchesLoading: loadingReducer(REQUEST_SAVED_SEARCHES, RECEIVE_SAVED_SEARCHES),
  variantSearchDisplay: createSingleObjectReducer(UPDATE_SEARCHED_VARIANT_DISPLAY, {
    sort: SORT_BY_XPOS,
    page: 1,
    recordsPerPage: 100,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

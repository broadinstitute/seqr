import { combineReducers } from 'redux'

import { loadProject, loadFamilyProject, loadAnalysisGroupProject, RECEIVE_DATA } from 'redux/rootReducer'
import { loadingReducer, createSingleObjectReducer, createSingleValueReducer, createObjectsByIdReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SORT_BY_XPOS } from 'shared/utils/constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'
const UPDATE_SEARCHED_VARIANT_DISPLAY = 'UPDATE_SEARCHED_VARIANT_DISPLAY'
const UPDATE_HASHED_SEARCHES = 'UPDATE_HASHED_SEARCHES'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'

// actions

export const loadProjectFamiliesContext = ({ projectGuid, familyGuid, analysisGroupGuid, searchHash }) => {
  // TODO initial analysisGroup
  if (projectGuid) {
    return loadProject(projectGuid)
  }
  if (familyGuid) {
    return loadFamilyProject(familyGuid)
  }
  if (analysisGroupGuid) {
    return loadAnalysisGroupProject(analysisGroupGuid)
  }
  if (searchHash) {
    return (dispatch, getState) => {
      const { projectFamilies } = getState().searchesByHash[searchHash] || {}
      if (projectFamilies) {
        projectFamilies.forEach(searchContext => loadProject(searchContext.projectGuid)(dispatch, getState))
      } else {
        dispatch({ type: REQUEST_PROJECT_DETAILS })
        new HttpRequestHelper(`/api/search_context/${searchHash}`,
          (responseJson) => {
            dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
            dispatch({ type: UPDATE_HASHED_SEARCHES, updatesById: { [searchHash]: responseJson.search } })
          },
          (e) => {
            dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
          },
        ).get()
      }
    }
  }
  return () => {}
}

export const saveHashedSearch = (searchHash, search) => {
  return (dispatch) => {
    dispatch({ type: UPDATE_HASHED_SEARCHES, updatesById: { [searchHash]: search } })
  }
}

export const loadSearchedVariants = ({ searchHash, displayUpdates, queryParams, updateQueryParams }) => {
  return (dispatch, getState) => {
    dispatch({ type: REQUEST_SEARCHED_VARIANTS })

    const state = getState()

    let { sort, page } = displayUpdates || queryParams
    if (!page) {
      page = 1
    }
    if (!sort) {
      sort = state.variantSearchDisplay.sort || SORT_BY_XPOS
    }

    // Update search table state and query params
    dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates: { sort: sort.toUpperCase(), page } })
    updateQueryParams({ sort: sort.toLowerCase(), page })

    const search = state.searchesByHash[searchHash]

    // Fetch variants
    new HttpRequestHelper(`/api/search/${searchHash}?sort=${sort.toLowerCase()}&page=${page || 1}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: responseJson.searchedVariants })
        dispatch({ type: UPDATE_HASHED_SEARCHES, updatesById: { [searchHash]: responseJson.search } })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, error: e.message, newValue: [] })
      },
    ).post(search)
  }
}


// reducers

export const reducers = {
  searchedVariants: createSingleValueReducer(RECEIVE_SEARCHED_VARIANTS, []),
  searchedVariantsLoading: loadingReducer(REQUEST_SEARCHED_VARIANTS, RECEIVE_SEARCHED_VARIANTS),
  searchesByHash: createObjectsByIdReducer(UPDATE_HASHED_SEARCHES),
  variantSearchDisplay: createSingleObjectReducer(UPDATE_SEARCHED_VARIANT_DISPLAY, {
    sort: SORT_BY_XPOS,
    page: 1,
    recordsPerPage: 100,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

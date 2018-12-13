import { combineReducers } from 'redux'
import hash from 'object-hash'

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

export const loadProjectFamiliesContext = ({ projectGuid, familyGuid, analysisGroupGuid, search }) => {
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
  if (search) {
    return (dispatch, getState) => {
      const { searchedProjectFamilies } = getState().searchesByHash[search] || {}
      if (searchedProjectFamilies) {
        searchedProjectFamilies.forEach(searchContext => loadProject(searchContext.projectGuid)(dispatch, getState))
      } else {
        dispatch({ type: REQUEST_PROJECT_DETAILS })
        new HttpRequestHelper(`/api/search_context/${search}`,
          (responseJson) => {
            dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
            dispatch({ type: UPDATE_HASHED_SEARCHES, updatesById: { [search]: responseJson.search } })
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

export const loadSearchedVariafnts = (searchHash, search) => {
  return (dispatch, getState) => {
    if (!searchHash) {
      return
    }
    const searchDisplay = search || getState().variantSearchDisplay
    const sort = (searchDisplay.sort || SORT_BY_XPOS).toLowerCase()

    dispatch({ type: REQUEST_SEARCHED_VARIANTS })
    new HttpRequestHelper(`/api/search/${searchHash}?sort=${sort}&page=${searchDisplay.page || 1}`,
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

export const updateVariantSearchfDisplay = (updates = {}, searchHash, search) => {
  return (dispatch, getState) => {
    dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates })
    return loadSearchedVariafnts(searchHash, search)(dispatch, getState)
  }
}

export const searchVariants = ({ searchHash, search, displayUpdates, updateQueryParams }) => {
  return (dispatch, getState) => {

    if (!searchHash) {
      if (search) {
        searchHash = hash.MD5(search)
        dispatch({ type: UPDATE_HASHED_SEARCHES, updatesById: { [searchHash]: search } })
      } else {
        return
      }
    }

    // Update search table state
    if (displayUpdates) {
      if (displayUpdates.sort) {
        displayUpdates.sort = displayUpdates.sort.toUpperCase()
      } else if ('sort' in displayUpdates) {
        displayUpdates.sort = SORT_BY_XPOS
      }

      if (!displayUpdates.page) {
        displayUpdates.page = 1
      }

      dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates: displayUpdates })
    }

    const searchDisplay = getState().variantSearchDisplay
    const sort = searchDisplay.sort.toLowerCase()
    const { page } = searchDisplay

    // Update query params
    const queryParams = { search: searchHash, sort }
    if (page) {
      queryParams.page = page
    }
    updateQueryParams(queryParams)

    // Fetch variants
    dispatch({ type: REQUEST_SEARCHED_VARIANTS })
    new HttpRequestHelper(`/api/search/${searchHash}?sort=${sort}&page=${page || 1}`,
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

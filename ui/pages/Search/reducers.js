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

export const loadSearchedVariants = (searchHash, search) => {
  return (dispatch, getState) => {
    if (!searchHash) {
      return
    }
    const searchDisplay = search || getState().variantSearchDisplay
    const sort = (searchDisplay.sort || SORT_BY_XPOS).toLowerCase()

    dispatch({ type: REQUEST_SEARCHED_VARIANTS })
    new HttpRequestHelper(`/api/search/${searchHash}?sort=${sort}&page=${searchDisplay.currentPage || 1}`,
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

export const updateVariantSearchDisplay = (updates, searchHash) => {
  return (dispatch, getState) => {
    dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates })
    return loadSearchedVariants(searchHash)(dispatch, getState)
  }
}


// reducers

export const reducers = {
  searchedVariants: createSingleValueReducer(RECEIVE_SEARCHED_VARIANTS, []),
  searchedVariantsLoading: loadingReducer(REQUEST_SEARCHED_VARIANTS, RECEIVE_SEARCHED_VARIANTS),
  searchesByHash: createObjectsByIdReducer(UPDATE_HASHED_SEARCHES),
  variantSearchDisplay: createSingleObjectReducer(UPDATE_SEARCHED_VARIANT_DISPLAY, {
    sort: SORT_BY_XPOS,
    currentPage: 1,
    recordsPerPage: 100,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

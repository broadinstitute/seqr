import { combineReducers } from 'redux'

import {
  updateEntity,
  RECEIVE_DATA,
  RECEIVE_SAVED_SEARCHES,
  REQUEST_SAVED_SEARCHES,
  REQUEST_SEARCHED_VARIANTS,
  RECEIVE_SEARCHED_VARIANTS,
} from 'redux/rootReducer'
import { loadingReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper, getUrlQueryString } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const UPDATE_COMPOUND_HET_DISPLAY = 'UPDATE_COMPOUND_HET_DISPLAY'
const REQUEST_SEARCH_CONTEXT = 'REQUEST_SEARCH_CONTEXT'
const RECEIVE_SEARCH_CONTEXT = 'RECEIVE_SEARCH_CONTEXT'
const REQUEST_MULTI_PROJECT_SEARCH_CONTEXT = 'REQUEST_MULTI_PROJECT_SEARCH_CONTEXT'
const RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT = 'RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT'

// actions

export const loadProjectFamiliesContext = ({ searchHash, projectGuid, familyGuids, analysisGroupGuid }, onSuccess) => {
  return (dispatch, getState) => {
    const state = getState()
    if (state.searchContextLoading.isLoading) {
      return
    }

    const contextParams = {}
    if (projectGuid && !(state.projectsByGuid[projectGuid] && state.projectsByGuid[projectGuid].variantTagTypes)) {
      contextParams.projectGuid = projectGuid
    }
    else if (familyGuids && familyGuids.length) {
      const [familyGuid] = familyGuids
      if (!state.familiesByGuid[familyGuid]) {
        contextParams.familyGuid = familyGuid
      }
    }
    else if (analysisGroupGuid && !state.analysisGroupsByGuid[analysisGroupGuid]) {
      contextParams.analysisGroupGuid = analysisGroupGuid
    } else if (searchHash && (!state.searchesByHash[searchHash] || !state.searchesByHash[searchHash].projectFamilies ||
        state.searchesByHash[searchHash].projectFamilies.some(entry => !state.projectsByGuid[entry.projectGuid]))) {
      dispatch({ type: REQUEST_MULTI_PROJECT_SEARCH_CONTEXT })
      contextParams.searchHash = searchHash
      contextParams.searchParams = state.searchesByHash[searchHash]
    }

    if (Object.keys(contextParams).length) {
      dispatch({ type: REQUEST_SEARCH_CONTEXT })
      const request = new HttpRequestHelper('/api/search_context',
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: responseJson })
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
          dispatch({ type: RECEIVE_SEARCH_CONTEXT })
          dispatch({ type: RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT })
        },
        (e) => {
          dispatch({ type: RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT })
          dispatch({ type: RECEIVE_SEARCH_CONTEXT, error: e.message })
        },
      ).post(contextParams)
      if (onSuccess) {
        request.then(() => onSuccess(getState()))
      }
    } else if (onSuccess) {
      onSuccess(getState())
    }
  }
}

export const loadProjectGroupContext = (projectCategoryGuid, addElementCallback) => {
  return (dispatch, getState) => {
    const state = getState()

    let loadedProjects = null
    if (state.projectCategoriesByGuid[projectCategoryGuid]) {
      const projects = Object.values(state.projectsByGuid).filter(({ projectCategoryGuids }) =>
        projectCategoryGuids.includes(projectCategoryGuid),
      )
      if (projects.every(project => project.variantTagTypes)) {
        loadedProjects = projects
      }
    }

    const addProjectElements = projects => projects.forEach(({ projectGuid }) => addElementCallback({
      projectGuid,
      familyGuids: Object.values(getState().familiesByGuid).filter(
        family => family.projectGuid === projectGuid).map(({ familyGuid }) => familyGuid),
    }))

    if (loadedProjects) {
      addProjectElements(loadedProjects)
    } else {
      dispatch({ type: REQUEST_SEARCH_CONTEXT })
      new HttpRequestHelper('/api/search_context',
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: responseJson })
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
          addProjectElements(Object.values(responseJson.projectsByGuid))
          dispatch({ type: RECEIVE_SEARCH_CONTEXT })
        },
        (e) => {
          dispatch({ type: RECEIVE_SEARCH_CONTEXT, error: e.message })
        },
      ).post({ projectCategoryGuid })
    }
  }
}

export const saveSearch = search => updateEntity(search, RECEIVE_SAVED_SEARCHES, '/api/saved_search', 'savedSearchGuid')

export const updateCompoundHetDisplay = ({ updates }) => {
  return (dispatch) => {
    dispatch({ type: UPDATE_COMPOUND_HET_DISPLAY, newValue: updates.flattenCompoundHet })
  }
}

export const loadSingleSearchedVariant = ({ variantId, familyGuid }) => {
  return (dispatch) => {
    const url = `/api/search/variant/${variantId}?${getUrlQueryString({ familyGuid })}`

    dispatch({ type: REQUEST_SEARCHED_VARIANTS })
    return new HttpRequestHelper(url,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: responseJson.searchedVariants })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, error: e.message, newValue: [] })
      },
    ).post()
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
  searchContextLoading: loadingReducer(REQUEST_SEARCH_CONTEXT, RECEIVE_SEARCH_CONTEXT),
  multiProjectSearchContextLoading: loadingReducer(REQUEST_MULTI_PROJECT_SEARCH_CONTEXT, RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT),
  flattenCompoundHet: createSingleValueReducer(UPDATE_COMPOUND_HET_DISPLAY, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

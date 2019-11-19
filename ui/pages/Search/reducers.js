import { combineReducers } from 'redux'

import { updateEntity, RECEIVE_DATA, RECEIVE_SAVED_SEARCHES, REQUEST_SAVED_SEARCHES } from 'redux/rootReducer'
import { loadingReducer, createSingleObjectReducer, createSingleValueReducer, createObjectsByIdReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper, getUrlQueryString } from 'shared/utils/httpRequestHelper'
import { SORT_BY_XPOS } from 'shared/utils/constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const UPDATE_CURRENT_SEARCH = 'UPDATE_CURRENT_SEARCH'
const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'
const REQUEST_SEARCH_GENE_BREAKDOWN = 'REQUEST_SEARCH_GENE_BREAKDOWN'
const RECEIVE_SEARCH_GENE_BREAKDOWN = 'RECEIVE_SEARCH_GENE_BREAKDOWN'
const UPDATE_SEARCHED_VARIANT_DISPLAY = 'UPDATE_SEARCHED_VARIANT_DISPLAY'
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
      new HttpRequestHelper('/api/search_context',
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

export const loadGeneBreakdown = (searchHash) => {
  return (dispatch, getState) => {
    if (!getState().searchGeneBreakdown[searchHash]) {
      dispatch({ type: REQUEST_SEARCH_GENE_BREAKDOWN })

      new HttpRequestHelper(`/api/search/${searchHash}/gene_breakdown`,
        (responseJson) => {
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
          dispatch({ type: RECEIVE_SEARCH_GENE_BREAKDOWN, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_SEARCH_GENE_BREAKDOWN, error: e.message, updatesById: {} })
        },
      ).get()
    }
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
  searchGeneBreakdown: createObjectsByIdReducer(RECEIVE_SEARCH_GENE_BREAKDOWN, 'searchGeneBreakdown'),
  searchGeneBreakdownLoading: loadingReducer(REQUEST_SEARCH_GENE_BREAKDOWN, RECEIVE_SEARCH_GENE_BREAKDOWN),
  searchContextLoading: loadingReducer(REQUEST_SEARCH_CONTEXT, RECEIVE_SEARCH_CONTEXT),
  multiProjectSearchContextLoading: loadingReducer(REQUEST_MULTI_PROJECT_SEARCH_CONTEXT, RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT),
  variantSearchDisplay: createSingleObjectReducer(UPDATE_SEARCHED_VARIANT_DISPLAY, {
    sort: SORT_BY_XPOS,
    page: 1,
    recordsPerPage: 100,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

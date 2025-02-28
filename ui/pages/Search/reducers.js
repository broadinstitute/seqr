import { combineReducers } from 'redux'

import {
  updateEntity,
  RECEIVE_DATA,
  RECEIVE_SAVED_SEARCHES,
} from 'redux/utils/reducerUtils'
import {
  loadingReducer,
  createSingleValueReducer,
  createObjectsByIdReducer,
  createSingleObjectReducer,
} from 'redux/utils/reducerFactories'
import { HttpRequestHelper, getUrlQueryString } from 'shared/utils/httpRequestHelper'
import { SORT_BY_XPOS } from 'shared/utils/constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const UPDATE_COMPOUND_HET_DISPLAY = 'UPDATE_COMPOUND_HET_DISPLAY'
const REQUEST_SEARCH_CONTEXT = 'REQUEST_SEARCH_CONTEXT'
const RECEIVE_SEARCH_CONTEXT = 'RECEIVE_SEARCH_CONTEXT'
const REQUEST_MULTI_PROJECT_SEARCH_CONTEXT = 'REQUEST_MULTI_PROJECT_SEARCH_CONTEXT'
const RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT = 'RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT'
const REQUEST_SAVED_SEARCHES = 'REQUEST_SAVED_SEARCHES'
const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'
const REQUEST_SEARCH_GENE_BREAKDOWN = 'REQUEST_SEARCH_GENE_BREAKDOWN'
const RECEIVE_SEARCH_GENE_BREAKDOWN = 'RECEIVE_SEARCH_GENE_BREAKDOWN'
const UPDATE_SEARCHED_VARIANT_DISPLAY = 'UPDATE_SEARCHED_VARIANT_DISPLAY'

// actions

export const loadProjectFamiliesContext = (
  { searchHash, projectGuid, familyGuids, analysisGroupGuid }, onSuccess,
) => (dispatch, getState) => {
  const state = getState()
  if (state.searchContextLoading.isLoading) {
    return
  }

  const contextParams = {}
  if (projectGuid && !(state.projectsByGuid[projectGuid] && state.projectsByGuid[projectGuid].locusListGuids &&
      state.projectsByGuid[projectGuid].familiesLoaded)) {
    contextParams.projectGuid = projectGuid
  } else if (familyGuids && familyGuids.length) {
    const [familyGuid] = familyGuids
    if (!state.familiesByGuid[familyGuid]) {
      contextParams.familyGuid = familyGuid
    }
  } else if (analysisGroupGuid && !state.analysisGroupsByGuid[analysisGroupGuid]) {
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
      }).post(contextParams)
    if (onSuccess) {
      request.then(() => onSuccess(getState()))
    }
  } else if (onSuccess) {
    onSuccess(getState())
  }
}

export const loadProjectGroupContext = (projectCategoryGuid, addElementCallback) => (dispatch, getState) => {
  const state = getState()

  let loadedProjects = null
  if (state.projectCategoriesByGuid[projectCategoryGuid]) {
    const projects = Object.values(state.projectsByGuid).filter(
      ({ projectCategoryGuids }) => projectCategoryGuids.includes(projectCategoryGuid),
    )
    if (projects.every(project => project.variantTagTypes)) {
      loadedProjects = projects
    }
  }

  const addProjectElements = projects => projects.forEach(({ projectGuid }) => addElementCallback({
    projectGuid,
    familyGuids: Object.values(getState().familiesByGuid).filter(
      family => family.projectGuid === projectGuid,
    ).map(({ familyGuid }) => familyGuid),
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
      }).post({ projectCategoryGuid })
  }
}

export const saveSearch = search => updateEntity(search, RECEIVE_SAVED_SEARCHES, '/api/saved_search', 'savedSearchGuid')

export const updateCompoundHetDisplay = updates => dispatch => dispatch(
  { type: UPDATE_COMPOUND_HET_DISPLAY, updates },
)

export const loadSingleSearchedVariant = ({ variantId, familyGuid }) => (dispatch) => {
  const url = `/api/search/variant/${variantId}?${getUrlQueryString({ familyGuid })}`

  dispatch({ type: REQUEST_SEARCHED_VARIANTS })
  return new HttpRequestHelper(url,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: responseJson.searchedVariants })
    },
    (e) => {
      dispatch({ type: RECEIVE_SEARCHED_VARIANTS, error: e.message, newValue: [] })
    }).post()
}

export const loadSavedSearches = () => (dispatch, getState) => {
  if (!Object.keys(getState().savedSearchesByGuid || {}).length) {
    dispatch({ type: REQUEST_SAVED_SEARCHES })

    new HttpRequestHelper('/api/saved_search/all',
      (responseJson) => {
        dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_SAVED_SEARCHES, error: e.message, updatesById: {} })
      }).get()
  }
}

export const updateSearchSort = updates => (dispatch) => {
  dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates })
}

export const loadSearchedVariants = (
  { searchHash }, { displayUpdates, queryParams, updateQueryParams },
) => (dispatch, getState) => {
  const state = getState()
  if (state.searchedVariantsLoading.isLoading) {
    return
  }

  dispatch({ type: REQUEST_SEARCHED_VARIANTS })

  let { sort, page } = displayUpdates || queryParams
  if (!page) {
    page = 1
  }
  if (!sort) {
    sort = state.variantSearchDisplay.sort || SORT_BY_XPOS
  }
  const urlQueryParams = { sort: sort.toLowerCase(), page }

  // Update search table state and query params
  dispatch({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates: { sort: sort.toUpperCase(), page } })
  updateQueryParams(urlQueryParams)

  const apiQueryParams = { ...urlQueryParams, loadFamilyContext: true, loadProjectTagTypes: true }
  const search = state.searchesByHash[searchHash]
  if (search && search.projectFamilies && search.projectFamilies.length > 0) {
    apiQueryParams.loadProjectTagTypes = search.projectFamilies.some(
      ({ projectGuid }) => !state.projectsByGuid[projectGuid]?.variantTagTypes,
    )
    apiQueryParams.loadFamilyContext = search.projectFamilies.some(
      ({ familyGuids }) => !familyGuids || familyGuids.some(
        familyGuid => !state.familiesByGuid[familyGuid]?.detailsLoaded,
      ),
    )
  }

  const url = `/api/search/${searchHash}?${getUrlQueryString(apiQueryParams)}`

  // Fetch variants
  new HttpRequestHelper(url,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: responseJson.searchedVariants })
      dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: { searchesByHash: { [searchHash]: responseJson.search } } })
    },
    (e) => {
      dispatch({ type: RECEIVE_SEARCHED_VARIANTS, error: e.message, newValue: [] })
    }).post(search)
}

export const unloadSearchResults = () => dispatch => dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: [] })

export const loadGeneBreakdown = searchHash => (dispatch, getState) => {
  if (!getState().searchGeneBreakdown[searchHash]) {
    dispatch({ type: REQUEST_SEARCH_GENE_BREAKDOWN })

    new HttpRequestHelper(`/api/search/${searchHash}/gene_breakdown`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_SEARCH_GENE_BREAKDOWN, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEARCH_GENE_BREAKDOWN, error: e.message, updatesById: {} })
      }).get()
  }
}

// reducers

export const reducers = {
  searchContextLoading: loadingReducer(REQUEST_SEARCH_CONTEXT, RECEIVE_SEARCH_CONTEXT),
  multiProjectSearchContextLoading: loadingReducer(
    REQUEST_MULTI_PROJECT_SEARCH_CONTEXT, RECEIVE_MULTI_PROJECT_SEARCH_CONTEXT,
  ),
  flattenCompoundHet: createSingleObjectReducer(UPDATE_COMPOUND_HET_DISPLAY),
  searchedVariants: createSingleValueReducer(RECEIVE_SEARCHED_VARIANTS, []),
  searchedVariantsLoading: loadingReducer(REQUEST_SEARCHED_VARIANTS, RECEIVE_SEARCHED_VARIANTS),
  searchGeneBreakdown: createObjectsByIdReducer(RECEIVE_SEARCH_GENE_BREAKDOWN, 'searchGeneBreakdown'),
  searchGeneBreakdownLoading: loadingReducer(REQUEST_SEARCH_GENE_BREAKDOWN, RECEIVE_SEARCH_GENE_BREAKDOWN),
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

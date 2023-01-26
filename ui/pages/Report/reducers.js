import { combineReducers } from 'redux'

import { loadingReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { GREGOR_PROJECT_PATH, CMG_PROJECT_PATH } from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_DISCOVERY_SHEET = 'REQUEST_DISCOVERY_SHEET'
const RECEIVE_DISCOVERY_SHEET = 'RECEIVE_DISCOVERY_SHEET'
const REQUEST_SAMPLE_METADATA = 'REQUEST_SAMPLE_METADATA'
const RECEIVE_SAMPLE_METADATA = 'RECEIVE_SAMPLE_METADATA'
const REQUEST_SEARCH_HASH_CONTEXT = 'REQUEST_SEARCH_HASH_CONTEXT'
const RECEIVE_SEARCH_HASH_CONTEXT = 'RECEIVE_SEARCH_HASH_CONTEXT'
const REQUEST_SEQR_STATS = 'REQUEST_SEQR_STATS'
const RECEIVE_SEQR_STATS = 'RECEIVE_SEQR_STATS'

// Data actions
const loadMultiProjectData = (requestAction, receiveAction, urlPath) => (projectGuid, filterValues) => (dispatch) => {
  if (projectGuid === GREGOR_PROJECT_PATH || projectGuid === CMG_PROJECT_PATH) {
    dispatch({ type: requestAction })

    const errors = new Set()
    const rows = []
    new HttpRequestHelper(`/api/report/get_category_projects/${projectGuid}`,
      (projectsResponseJson) => {
        const chunkedProjects = projectsResponseJson.projectGuids.reduce((acc, guid) => {
          if (acc[0].length === 5) {
            acc.unshift([])
          }
          acc[0].push(guid)
          return acc
        }, [[]])
        chunkedProjects.reduce((previousPromise, projectsChunk) => previousPromise.then(
          () => Promise.all(projectsChunk.map(cmgProjectGuid => new HttpRequestHelper(
            `/api/report/${urlPath}/${cmgProjectGuid}`,
            (responseJson) => {
              rows.push(...responseJson.rows)
            },
            e => errors.add(e.message),
          ).get())),
        ), Promise.resolve()).then(() => {
          if (errors.size) {
            dispatch({ type: receiveAction, error: [...errors].join(', '), newValue: [] })
          } else {
            dispatch({ type: receiveAction, newValue: rows })
          }
        })
      },
      (e) => {
        dispatch({ type: receiveAction, error: e.message, newValue: [] })
      }).get(filterValues)
  } else if (projectGuid) {
    dispatch({ type: requestAction })
    new HttpRequestHelper(`/api/report/${urlPath}/${projectGuid}`,
      (responseJson) => {
        dispatch({ type: receiveAction, newValue: responseJson.rows })
      },
      (e) => {
        dispatch({ type: receiveAction, error: e.message, newValue: [] })
      }).get(filterValues)
  }
}

export const loadDiscoverySheet = loadMultiProjectData(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET, 'discovery_sheet')

export const loadSampleMetadata = loadMultiProjectData(REQUEST_SAMPLE_METADATA, RECEIVE_SAMPLE_METADATA, 'sample_metadata')

export const loadSeqrStats = () => (dispatch) => {
  dispatch({ type: REQUEST_SEQR_STATS })
  new HttpRequestHelper('/api/report/seqr_stats',
    (responseJson) => {
      dispatch({ type: RECEIVE_SEQR_STATS, newValue: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_SEQR_STATS, error: e.message, newValue: {} })
    }).get()
}

export const loadSearchHashContext = searchHash => (dispatch, getState) => {
  if (!searchHash) {
    return
  }
  const state = getState()
  if (state.searchHashContextLoading.isLoading) {
    return
  }

  if (!state.searchesByHash[searchHash] || !state.searchesByHash[searchHash].projectGuids ||
      state.searchesByHash[searchHash].projectGuids.some(projectGuid => !state.projectsByGuid[projectGuid])) {
    dispatch({ type: REQUEST_SEARCH_HASH_CONTEXT })
    new HttpRequestHelper('/api/search_context',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_SEARCH_HASH_CONTEXT })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEARCH_HASH_CONTEXT, error: e.message })
      }).post({ searchHash, searchParams: state.searchesByHash[searchHash] })
  }
}

export const loadProjectContext = projectGuid => (dispatch, getState) => {
  const state = getState()
  if (state.searchHashContextLoading.isLoading) {
    return
  }
  const project = state.projectsByGuid[projectGuid]
  if (!project || !project.variantTagTypes) {
    new HttpRequestHelper('/api/search_context',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).post({ projectGuid })
  }
}

export const loadProjectGroupContext = (projectCategoryGuid, addElementCallback) => (dispatch, getState) => {
  const state = getState()

  if (state.projectCategoriesByGuid[projectCategoryGuid]) {
    Object.values(state.projectsByGuid).filter(
      ({ projectCategoryGuids }) => projectCategoryGuids.includes(projectCategoryGuid),
    ).forEach(({ projectGuid }) => addElementCallback(projectGuid))
  } else {
    new HttpRequestHelper('/api/search_context',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        Object.keys(responseJson.projectsByGuid).forEach(projectGuid => addElementCallback(projectGuid))
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).post({ projectCategoryGuid })
  }
}

export const reducers = {
  sampleMetadataLoading: loadingReducer(REQUEST_SAMPLE_METADATA, RECEIVE_SAMPLE_METADATA),
  sampleMetadataRows: createSingleValueReducer(RECEIVE_SAMPLE_METADATA, []),
  discoverySheetLoading: loadingReducer(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET),
  discoverySheetRows: createSingleValueReducer(RECEIVE_DISCOVERY_SHEET, []),
  searchHashContextLoading: loadingReducer(REQUEST_SEARCH_HASH_CONTEXT, RECEIVE_SEARCH_HASH_CONTEXT),
  seqrStatsLoading: loadingReducer(REQUEST_SEQR_STATS, RECEIVE_SEQR_STATS),
  seqrStats: createSingleValueReducer(RECEIVE_SEQR_STATS, {}),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

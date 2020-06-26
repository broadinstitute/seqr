import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import { loadingReducer, createSingleValueReducer, createSingleObjectReducer } from 'redux/utils/reducerFactories'
import { RECEIVE_DATA, REQUEST_SAVED_VARIANTS, REQUEST_PROJECTS, loadProject } from 'redux/rootReducer'
import { SHOW_ALL, SORT_BY_XPOS } from 'shared/utils/constants'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_DISCOVERY_SHEET = 'REQUEST_DISCOVERY_SHEET'
const RECEIVE_DISCOVERY_SHEET = 'RECEIVE_DISCOVERY_SHEET'
const REQUEST_SUCCESS_STORY = 'REQUEST_SUCCESS_STORY'
const RECEIVE_SUCCESS_STORY = 'RECEIVE_SUCCESS_STORY'
const REQUEST_ELASTICSEARCH_STATUS = 'REQUEST_ELASTICSEARCH_STATUS'
const RECEIVE_ELASTICSEARCH_STATUS = 'RECEIVE_ELASTICSEARCH_STATUS'
const REQUEST_MME = 'REQUEST_MME'
const RECEIVE_MME = 'RECEIVE_MME'
const REQUEST_SAMPLE_METADATA = 'REQUEST_SAMPLE_METADATA'
const RECEIVE_SAMPLE_METADATA = 'RECEIVE_SAMPLE_METADATA'
const RECEIVE_SAVED_VARIANT_TAGS = 'RECEIVE_SAVED_VARIANT_TAGS'
const REQUEST_SEARCH_HASH_CONTEXT = 'REQUEST_SEARCH_HASH_CONTEXT'
const RECEIVE_SEARCH_HASH_CONTEXT = 'RECEIVE_SEARCH_HASH_CONTEXT'
const REQUEST_SEQR_STATS = 'REQUEST_SEQR_STATS'
const RECEIVE_SEQR_STATS = 'RECEIVE_SEQR_STATS'
const RECEIVE_PIPELINE_UPLOAD_STATS = 'RECEIVE_PIPELINE_UPLOAD_STATS'
const UPDATE_STAFF_SAVED_VARIANT_TABLE_STATE = 'UPDATE_STAFF_VARIANT_STATE'


// Data actions
export const loadElasticsearchStatus = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_ELASTICSEARCH_STATUS })
    new HttpRequestHelper('/api/staff/elasticsearch_status',
      (responseJson) => {
        dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, newValue: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, error: e.message, newValue: { errors: [e.message] } })
      },
    ).get()
  }
}

export const loadMme = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_MME })
    new HttpRequestHelper('/api/staff/matchmaker',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_MME, newValue: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_MME, error: e.message, newValue: [] })
      },
    ).get()
  }
}

const loadMultiProjectData = (requestAction, receiveAction, urlPath) => (projectGuid, filterValues) => {
  return (dispatch) => {
    if (projectGuid === 'all') {
      dispatch({ type: requestAction })

      const errors = new Set()
      const rows = []
      new HttpRequestHelper('/api/staff/projects_for_category/CMG',
        (projectsResponseJson) => {
          const chunkedProjects = projectsResponseJson.projectGuids.reduce((acc, guid) => {
            if (acc[0].length === 5) {
              acc.unshift([])
            }
            acc[0].push(guid)
            return acc
          }, [[]])
          chunkedProjects.reduce((previousPromise, projectsChunk) => {
            return previousPromise.then(() => {
              return Promise.all(projectsChunk.map(cmgProjectGuid =>
                new HttpRequestHelper(`/api/staff/${urlPath}/${cmgProjectGuid}`,
                  (responseJson) => {
                    if (responseJson.errors && responseJson.errors.length) {
                      console.log(responseJson.errors)
                    }
                    rows.push(...responseJson.rows)
                  },
                  e => errors.add(e.message),
                ).get(),
              ))
            })
          }, Promise.resolve()).then(() => {
            if (errors.size) {
              dispatch({ type: receiveAction, error: [...errors].join(', '), newValue: [] })
            } else {
              dispatch({ type: receiveAction, newValue: rows })
            }
          })
        },
        (e) => {
          dispatch({ type: receiveAction, error: e.message, newValue: [] })
        },
      ).get(filterValues)
    }

    else if (projectGuid) {
      dispatch({ type: requestAction })
      new HttpRequestHelper(`/api/staff/${urlPath}/${projectGuid}`,
        (responseJson) => {
          console.log(responseJson.errors)
          dispatch({ type: receiveAction, newValue: responseJson.rows })
        },
        (e) => {
          dispatch({ type: receiveAction, error: e.message, newValue: [] })
        },
      ).get(filterValues)
    }
  }
}

export const loadDiscoverySheet = loadMultiProjectData(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET, 'discovery_sheet')

export const loadSampleMetadata = loadMultiProjectData(REQUEST_SAMPLE_METADATA, RECEIVE_SAMPLE_METADATA, 'sample_metadata')

export const loadSuccessStory = (successStoryTypes) => {
  return (dispatch) => {
    if (successStoryTypes) {
      dispatch({ type: REQUEST_SUCCESS_STORY })
      new HttpRequestHelper(`/api/staff/success_story/${successStoryTypes}`,
        (responseJson) => {
          console.log(responseJson.errors)
          dispatch({ type: RECEIVE_SUCCESS_STORY, newValue: responseJson.rows })
        },
        (e) => {
          dispatch({ type: RECEIVE_SUCCESS_STORY, error: e.message, newValue: [] })
        },
      ).get()
    }
  }
}


export const createStaffUser = (values) => {
  return () => {
    return new HttpRequestHelper('/api/users/create_staff_user',
      () => {},
      (e) => {
        if (e.body && e.body.error) {
          throw new SubmissionError({ _error: [e.body.error] })
        } else {
          throw new SubmissionError({ _error: [e.message] })
        }
      },
    ).post(values)
  }
}

export const loadSeqrStats = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_SEQR_STATS })
    new HttpRequestHelper('/api/staff/seqr_stats',
      (responseJson) => {
        dispatch({ type: RECEIVE_SEQR_STATS, newValue: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEQR_STATS, error: e.message, newValue: {} })
      },
    ).get()
  }
}

export const uploadQcPipelineOutput = (values) => {
  return (dispatch) => {
    return new HttpRequestHelper('/api/staff/upload_qc_pipeline_output',
      (responseJson) => {
        dispatch({ type: RECEIVE_PIPELINE_UPLOAD_STATS, newValue: responseJson })
      },
      (e) => {
        if (e.body && e.body.errors) {
          throw new SubmissionError({ _error: e.body.errors })
        } else {
          throw new SubmissionError({ _error: [e.message] })
        }
      },
    ).post(values)
  }
}

export const loadSavedVariants = ({ tag, gene = '' }) => {
  return (dispatch, getState) => {
    // Do not load if already loaded
    if (tag) {
      if (getState().savedVariantTags[tag]) {
        return
      }
    } else if (!gene) {
      return
    }

    dispatch({ type: REQUEST_SAVED_VARIANTS })
    new HttpRequestHelper(`/api/staff/saved_variants/${tag}`,
      (responseJson) => {
        if (tag && !gene) {
          dispatch({
            type: RECEIVE_SAVED_VARIANT_TAGS,
            updates: { [tag]: true },
          })
        }
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      },
    ).get({ gene })
  }
}

export const loadSearchHashContext = (searchHash) => {
  return (dispatch, getState) => {
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
        },
      ).post({ searchHash, searchParams: state.searchesByHash[searchHash] })
    }
  }
}

export const loadProjectContext = (projectGuid) => {
  return (dispatch, getState) => {
    const state = getState()
    if (state.searchHashContextLoading.isLoading) {
      return
    }
    loadProject(projectGuid)(dispatch, getState)
  }
}

export const loadProjectGroupContext = (projectCategoryGuid, addElementCallback) => {
  return (dispatch, getState) => {
    const state = getState()

    if (state.projectCategoriesByGuid[projectCategoryGuid]) {
      Object.values(state.projectsByGuid).filter(({ projectCategoryGuids }) =>
        projectCategoryGuids.includes(projectCategoryGuid),
      ).forEach(({ projectGuid }) => addElementCallback(projectGuid))
    }

    else {
      dispatch({ type: REQUEST_PROJECTS })
      new HttpRequestHelper('/api/search_context',
        (responseJson) => {
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
          Object.keys(responseJson.projectsByGuid).forEach(projectGuid => addElementCallback(projectGuid))
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).post({ projectCategoryGuid })
    }
  }
}

export const updateStaffSavedVariantTable = updates => ({ type: UPDATE_STAFF_SAVED_VARIANT_TABLE_STATE, updates })

export const reducers = {
  sampleMetadataLoading: loadingReducer(REQUEST_SAMPLE_METADATA, RECEIVE_SAMPLE_METADATA),
  sampleMetadataRows: createSingleValueReducer(RECEIVE_SAMPLE_METADATA, []),
  discoverySheetLoading: loadingReducer(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET),
  discoverySheetRows: createSingleValueReducer(RECEIVE_DISCOVERY_SHEET, []),
  successStoryLoading: loadingReducer(REQUEST_SUCCESS_STORY, RECEIVE_SUCCESS_STORY),
  successStoryRows: createSingleValueReducer(RECEIVE_SUCCESS_STORY, []),
  elasticsearchStatusLoading: loadingReducer(REQUEST_ELASTICSEARCH_STATUS, RECEIVE_ELASTICSEARCH_STATUS),
  elasticsearchStatus: createSingleValueReducer(RECEIVE_ELASTICSEARCH_STATUS, {}),
  mmeLoading: loadingReducer(REQUEST_MME, RECEIVE_MME),
  mmeMetrics: createSingleValueReducer(RECEIVE_MME, {}, 'metrics'),
  mmeSubmissions: createSingleValueReducer(RECEIVE_MME, [], 'submissions'),
  projectGroupContextLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_DATA),
  savedVariantTags: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_TAGS),
  searchHashContextLoading: loadingReducer(REQUEST_SEARCH_HASH_CONTEXT, RECEIVE_SEARCH_HASH_CONTEXT),
  seqrStatsLoading: loadingReducer(REQUEST_SEQR_STATS, RECEIVE_SEQR_STATS),
  seqrStats: createSingleValueReducer(RECEIVE_SEQR_STATS, {}),
  qcUploadStats: createSingleValueReducer(RECEIVE_PIPELINE_UPLOAD_STATS, {}),
  staffSavedVariantTableState: createSingleObjectReducer(UPDATE_STAFF_SAVED_VARIANT_TABLE_STATE, {
    categoryFilter: SHOW_ALL,
    sort: SORT_BY_XPOS,
    page: 1,
    recordsPerPage: 25,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

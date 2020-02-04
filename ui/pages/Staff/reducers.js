import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import { loadingReducer, createSingleValueReducer, createSingleObjectReducer } from 'redux/utils/reducerFactories'
import { RECEIVE_DATA, REQUEST_SAVED_VARIANTS } from 'redux/rootReducer'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_ANVIL = 'REQUEST_ANVIL'
const RECEIVE_ANVIL = 'RECEIVE_ANVIL'
const REQUEST_DISCOVERY_SHEET = 'REQUEST_DISCOVERY_SHEET'
const RECEIVE_DISCOVERY_SHEET = 'RECEIVE_DISCOVERY_SHEET'
const REQUEST_SUCCESS_STORY = 'REQUEST_SUCCESS_STORY'
const RECEIVE_SUCCESS_STORY = 'RECEIVE_SUCCESS_STORY'
const REQUEST_ELASTICSEARCH_STATUS = 'REQUEST_ELASTICSEARCH_STATUS'
const RECEIVE_ELASTICSEARCH_STATUS = 'RECEIVE_ELASTICSEARCH_STATUS'
const REQUEST_MME = 'REQUEST_MME'
const RECEIVE_MME = 'RECEIVE_MME'
const RECEIVE_SAVED_VARIANT_TAGS = 'RECEIVE_SAVED_VARIANT_TAGS'
const REQUEST_SEQR_STATS = 'REQUEST_SEQR_STATS'
const RECEIVE_SEQR_STATS = 'RECEIVE_SEQR_STATS'
const RECEIVE_PIPELINE_UPLOAD_STATS = 'RECEIVE_PIPELINE_UPLOAD_STATS'


// Data actions

export const loadAnvil = (projectGuid, filterValues) => {
  return (dispatch) => {
    if (projectGuid) {
      dispatch({ type: REQUEST_ANVIL })
      new HttpRequestHelper(`/api/staff/anvil/${projectGuid}`,
        (responseJson) => {
          dispatch({ type: RECEIVE_ANVIL, newValue: responseJson.anvilRows })
        },
        (e) => {
          dispatch({ type: RECEIVE_ANVIL, error: e.message, newValue: [] })
        },
      ).get(filterValues)
    }
  }
}

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

export const loadDiscoverySheet = (projectGuid) => {
  return (dispatch) => {
    if (projectGuid === 'all') {
      dispatch({ type: REQUEST_DISCOVERY_SHEET })

      const errors = new Set()
      const rows = []
      new HttpRequestHelper('/api/staff/projects_for_category/CMG',
        (projectsResponseJson) => {
          Promise.all(projectsResponseJson.projectGuids.map(cmgProjectGuid =>
            new HttpRequestHelper(`/api/staff/discovery_sheet/${cmgProjectGuid}`,
              (responseJson) => {
                if (responseJson.errors.length) {
                  console.log(responseJson.errors)
                }
                rows.push(...responseJson.rows)
              },
              e => errors.add(e.message),
            ).get(),
          )).then(() => {
            if (errors.length) {
              dispatch({ type: RECEIVE_DISCOVERY_SHEET, error: [...errors].join(', '), newValue: [] })
            } else {
              dispatch({ type: RECEIVE_DISCOVERY_SHEET, newValue: rows })
            }
          })
        },
        (e) => {
          dispatch({ type: RECEIVE_DISCOVERY_SHEET, error: e.message, newValue: [] })
        },
      ).get()
    }

    else if (projectGuid) {
      dispatch({ type: REQUEST_DISCOVERY_SHEET })
      new HttpRequestHelper(`/api/staff/discovery_sheet/${projectGuid}`,
        (responseJson) => {
          console.log(responseJson.errors)
          dispatch({ type: RECEIVE_DISCOVERY_SHEET, newValue: responseJson.rows })
        },
        (e) => {
          dispatch({ type: RECEIVE_DISCOVERY_SHEET, error: e.message, newValue: [] })
        },
      ).get()
    }
  }
}

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
    } else {
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

export const reducers = {
  anvilLoading: loadingReducer(REQUEST_ANVIL, RECEIVE_ANVIL),
  anvilRows: createSingleValueReducer(RECEIVE_ANVIL, []),
  discoverySheetLoading: loadingReducer(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET),
  discoverySheetRows: createSingleValueReducer(RECEIVE_DISCOVERY_SHEET, []),
  successStoryLoading: loadingReducer(REQUEST_SUCCESS_STORY, RECEIVE_SUCCESS_STORY),
  successStoryRows: createSingleValueReducer(RECEIVE_SUCCESS_STORY, []),
  elasticsearchStatusLoading: loadingReducer(REQUEST_ELASTICSEARCH_STATUS, RECEIVE_ELASTICSEARCH_STATUS),
  elasticsearchStatus: createSingleValueReducer(RECEIVE_ELASTICSEARCH_STATUS, {}),
  mmeLoading: loadingReducer(REQUEST_MME, RECEIVE_MME),
  mmeMetrics: createSingleValueReducer(RECEIVE_MME, {}, 'metrics'),
  mmeSubmissions: createSingleValueReducer(RECEIVE_MME, [], 'submissions'),
  savedVariantTags: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_TAGS),
  seqrStatsLoading: loadingReducer(REQUEST_SEQR_STATS, RECEIVE_SEQR_STATS),
  seqrStats: createSingleValueReducer(RECEIVE_SEQR_STATS, {}),
  qcUploadStats: createSingleValueReducer(RECEIVE_PIPELINE_UPLOAD_STATS, {}),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

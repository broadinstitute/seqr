import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import { loadingReducer, createSingleValueReducer, createSingleObjectReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_ELASTICSEARCH_STATUS = 'REQUEST_ELASTICSEARCH_STATUS'
const RECEIVE_ELASTICSEARCH_STATUS = 'RECEIVE_ELASTICSEARCH_STATUS'
const RECEIVE_PIPELINE_UPLOAD_STATS = 'RECEIVE_PIPELINE_UPLOAD_STATS'
const REQUEST_ALL_USERS = 'REQUEST_ALL_USERS'
const RECEIVE_ALL_USERS = 'RECEIVE_ALL_USERS'


// Data actions
export const loadElasticsearchStatus = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_ELASTICSEARCH_STATUS })
    new HttpRequestHelper('/api/data_management/elasticsearch_status',
      (responseJson) => {
        dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, updates: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, error: e.message, updates: { errors: [e.message] } })
      },
    ).get()
  }
}

export const loadAllUsers = () => {
  return (dispatch, getState) => {
    const { allUsers } = getState()
    if (allUsers && allUsers.length) {
      return
    }

    dispatch({ type: REQUEST_ALL_USERS })
    new HttpRequestHelper('/api/data_management/get_all_users',
      (responseJson) => {
        dispatch({ type: RECEIVE_ALL_USERS, newValue: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_ALL_USERS, error: e.message, newValue: [] })
      },
    ).get()
  }
}

export const uploadQcPipelineOutput = (values) => {
  return (dispatch) => {
    return new HttpRequestHelper('/api/data_management/upload_qc_pipeline_output',
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

export const deleteEsIndex = (index) => {
  return (dispatch) => {
    return new HttpRequestHelper('/api/data_management/delete_index',
      (responseJson) => {
        dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, updates: responseJson })
      },
      (e) => {
        if (e.body && e.body.error) {
          throw new SubmissionError({ _error: [e.body.error] })
        } else {
          throw new SubmissionError({ _error: [e.message] })
        }
      },
    ).post({ index })
  }
}

export const reducers = {
  elasticsearchStatusLoading: loadingReducer(REQUEST_ELASTICSEARCH_STATUS, RECEIVE_ELASTICSEARCH_STATUS),
  elasticsearchStatus: createSingleObjectReducer(RECEIVE_ELASTICSEARCH_STATUS),
  qcUploadStats: createSingleValueReducer(RECEIVE_PIPELINE_UPLOAD_STATS, {}),
  allUsers: createSingleValueReducer(RECEIVE_ALL_USERS, [], 'users'),
  allUsersLoading: loadingReducer(REQUEST_ALL_USERS, RECEIVE_ALL_USERS),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import { loadingReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { RECEIVE_DATA } from 'redux/rootReducer'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_ANVIL = 'REQUEST_ANVIL'
const RECEIVE_ANVIL = 'RECEIVE_ANVIL'
const REQUEST_DISCOVERY_SHEET = 'REQUEST_DISCOVERY_SHEET'
const RECEIVE_DISCOVERY_SHEET = 'RECEIVE_DISCOVERY_SHEET'
const REQUEST_ELASTICSEARCH_STATUS = 'REQUEST_ELASTICSEARCH_STATUS'
const RECEIVE_ELASTICSEARCH_STATUS = 'RECEIVE_ELASTICSEARCH_STATUS'
const REQUEST_MME_METRICS = 'REQUEST_MME_METRICS'
const RECEIVE_MME_METRICS = 'RECEIVE_MME_METRICS'
const REQUEST_MME_SUBMISSIONS = 'REQUEST_MME_SUBMISSIONS'
const RECEIVE_MME_SUBMISSIONS = 'RECEIVE_MME_SUBMISSIONS'


// Data actions

export const loadAnvil = (projectGuid) => {
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
      ).get()
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

export const loadMmeMetrics = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_MME_METRICS })
    new HttpRequestHelper('/api/staff/matchmaker_metrics',
      (responseJson) => {
        dispatch({ type: RECEIVE_MME_METRICS, newValue: responseJson.metrics })
      },
      (e) => {
        dispatch({ type: RECEIVE_MME_METRICS, error: e.message, newValue: {} })
      },
    ).get()
  }
}

export const loadMmeSubmissions = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_MME_SUBMISSIONS })
    new HttpRequestHelper('/api/staff/matchmaker_submissions',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_MME_SUBMISSIONS, newValue: responseJson.submissions })
      },
      (e) => {
        dispatch({ type: RECEIVE_MME_SUBMISSIONS, error: e.message, newValue: [] })
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

export const reducers = {
  anvilLoading: loadingReducer(REQUEST_ANVIL, RECEIVE_ANVIL),
  anvilRows: createSingleValueReducer(RECEIVE_ANVIL, []),
  discoverySheetLoading: loadingReducer(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET),
  discoverySheetRows: createSingleValueReducer(RECEIVE_DISCOVERY_SHEET, []),
  elasticsearchStatusLoading: loadingReducer(REQUEST_ELASTICSEARCH_STATUS, RECEIVE_ELASTICSEARCH_STATUS),
  elasticsearchStatus: createSingleValueReducer(RECEIVE_ELASTICSEARCH_STATUS, {}),
  mmeMetricsLoading: loadingReducer(REQUEST_MME_METRICS, RECEIVE_MME_METRICS),
  mmeMetrics: createSingleValueReducer(RECEIVE_MME_METRICS, {}),
  mmeSubmissionsLoading: loadingReducer(REQUEST_MME_SUBMISSIONS, RECEIVE_MME_SUBMISSIONS),
  mmeSubmissions: createSingleValueReducer(RECEIVE_MME_SUBMISSIONS, []),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

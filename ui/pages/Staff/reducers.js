import { combineReducers } from 'redux'

import { loadingReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_ANVIL = 'REQUEST_ANVIL'
const RECEIVE_ANVIL = 'RECEIVE_ANVIL'
const REQUEST_DISCOVERY_SHEET = 'REQUEST_DISCOVERY_SHEET'
const RECEIVE_DISCOVERY_SHEET = 'RECEIVE_DISCOVERY_SHEET'


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

export const reducers = {
  anvilLoading: loadingReducer(REQUEST_ANVIL, RECEIVE_ANVIL),
  anvilRows: createSingleValueReducer(RECEIVE_ANVIL, []),
  discoverySheetLoading: loadingReducer(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET),
  discoverySheetRows: createSingleValueReducer(RECEIVE_DISCOVERY_SHEET, []),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

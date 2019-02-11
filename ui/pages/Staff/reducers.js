import { combineReducers } from 'redux'

import { loadingReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_ANVIL = 'REQUEST_ANVIL'
const RECEIVE_ANVIL = 'RECEIVE_ANVIL'


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

export const reducers = {
  anvilLoading: loadingReducer(REQUEST_ANVIL, RECEIVE_ANVIL),
  anvilRows: createSingleValueReducer(RECEIVE_ANVIL, []),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

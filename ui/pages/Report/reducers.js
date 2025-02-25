import { combineReducers } from 'redux'

import { loadingReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_DISCOVERY_SHEET = 'REQUEST_DISCOVERY_SHEET'
const RECEIVE_DISCOVERY_SHEET = 'RECEIVE_DISCOVERY_SHEET'
const REQUEST_SEQR_STATS = 'REQUEST_SEQR_STATS'
const RECEIVE_SEQR_STATS = 'RECEIVE_SEQR_STATS'

// Data actions

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

export const reducers = {
  discoverySheetLoading: loadingReducer(REQUEST_DISCOVERY_SHEET, RECEIVE_DISCOVERY_SHEET),
  discoverySheetRows: createSingleValueReducer(RECEIVE_DISCOVERY_SHEET, []),
  seqrStatsLoading: loadingReducer(REQUEST_SEQR_STATS, RECEIVE_SEQR_STATS),
  seqrStats: createSingleValueReducer(RECEIVE_SEQR_STATS, {}),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

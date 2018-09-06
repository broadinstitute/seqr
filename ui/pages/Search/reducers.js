import { combineReducers } from 'redux'

import { loadingReducer, createSingleObjectReducer, createSingleValueReducer, createObjectsByIdReducer } from 'redux/utils/reducerFactories'
import { RECEIVE_DATA } from 'redux/rootReducer'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SORT_BY_XPOS } from 'shared/utils/constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'
const UPDATE_SEARCHED_VARIANT_DISPLAY = 'UPDATE_SEARCHED_VARIANT_DISPLAY'
const UPDATE_HASHED_SEARCHES = 'UPDATE_HASHED_SEARCHES'

// actions

export const loadSearchedVariants = (searchHash, search) => {
  return (dispatch, getState) => {
    search = search || getState().searchesByHash[searchHash] // TODO once caching do not use this defaulting
    if (!search) {
      return
    }
    dispatch({ type: REQUEST_SEARCHED_VARIANTS })
    new HttpRequestHelper('/api/search',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, newValue: responseJson.searchedVariants })
        dispatch({ type: UPDATE_HASHED_SEARCHES, updatesById: { [searchHash]: responseJson.search } })
      },
      (e) => {
        dispatch({ type: RECEIVE_SEARCHED_VARIANTS, error: e.message, newValue: [] })
      },
    ).post(search)
  }
}

export const updateVariantSearchDisplay = updates => ({ type: UPDATE_SEARCHED_VARIANT_DISPLAY, updates })

// reducers

export const reducers = {
  searchedVariants: createSingleValueReducer(RECEIVE_SEARCHED_VARIANTS, []),
  searchedVariantsLoading: loadingReducer(REQUEST_SEARCHED_VARIANTS, RECEIVE_SEARCHED_VARIANTS),
  searchesByHash: createObjectsByIdReducer(UPDATE_HASHED_SEARCHES),
  variantSearchDisplay: createSingleObjectReducer(UPDATE_SEARCHED_VARIANT_DISPLAY, {
    hideExcluded: false,
    sortOrder: SORT_BY_XPOS,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

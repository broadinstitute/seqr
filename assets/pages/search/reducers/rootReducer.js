import { combineReducers } from 'redux'

import searchParams from './searchParams'
import searchStatus, * as fromSearchStatus from './searchStatus'
import searchResults from './searchResults'

// reducer
const rootReducer = combineReducers({
    searchParams,
    searchStatus,
    searchResults,
});


export default rootReducer;


// selectors
export const getSearchParams = (state) => state.searchParams
export const getSearchStatus = (state) => state.searchStatus
export const getSearchResults = (state) => state.searchResults

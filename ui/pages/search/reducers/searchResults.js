import { SET_SEARCH_RESULT } from  '../actions/searchResults';

import { getSearchResults } from '../reducers/rootReducer'


// reducer
export default function searchResults(state = {
    results: [],   //default state
}, action) {
    switch (action.type) {

        case SET_SEARCH_RESULT:
            return {
                results: action.results
            }

        default:
            return state
    }
}


// selector

export const getResults = (state) => getSearchResults(state).results
import 'whatwg-fetch'

import { setSearchResults } from './searchResults'

import { getSearchInProgressId } from '../reducers/searchStatus'


// actions
export const START_SEARCH = 'START_SEARCH'
export const CANCEL_SEARCH = 'CANCEL_SEARCH'
export const END_SEARCH_SUCCESSFULLY = 'END_SEARCH_SUCCESSFULLY'
export const END_SEARCH_WITH_ERROR = 'END_SEARCH_WITH_ERROR'


var searchIdGenerator = 0;

// action creators
export const startSearch = (searchParams) => {

    return (dispatch, getState) => {
        const mySearchId = ++searchIdGenerator  //create a unique id, in case multiple searches are started at once

        dispatch({ type: START_SEARCH, searchId: mySearchId })

        fetch('/seqr/variants', {
            method: 'POST',
            credentials: 'include',
            body: JSON.stringify(searchParams),
        })
        .then((response) => {
            if (getSearchInProgressId(getState()) !== mySearchId)
                return;

            if (response.status !== 200) {
                throw new Error("network error: " + response.status)
            }

            return response.json()
        })
        .then((json) => {
            setSearchResults(json['results'])

            dispatch(endSearchSuccessfully())

        })
        .catch((error) => {
            if(getSearchInProgressId(getState()) !== mySearchId)
                return

            dispatch(endSearchWithError(error.message))

        })
    }
}

export const cancelSearch = () => ({ type: CANCEL_SEARCH })
export const endSearchSuccessfully = () => ({ type: END_SEARCH_SUCCESSFULLY })
export const endSearchWithError = (errorMessage) => ({ type: END_SEARCH_WITH_ERROR, errorMessage: errorMessage })


import { START_SEARCH, CANCEL_SEARCH, SHOW_CANCEL_BUTTON, END_SEARCH_SUCCESSFULLY, END_SEARCH_WITH_ERROR } from '../actions/searchStatus'

import { getSearchStatus } from '../reducers/rootReducer'

// reducer
export default function searchStatus(state = {   //default state
    inProgress: null,
    errorMessage: null,
}, action) {
    switch (action.type) {

        case START_SEARCH:
            return {
                inProgress: action.searchId,
                errorMessage: null,
            }

        case CANCEL_SEARCH:
        case END_SEARCH_SUCCESSFULLY:
            return {
                inProgress: null,
                errorMessage: null,
            }

        case END_SEARCH_WITH_ERROR:
            return {
                inProgress: null,
                errorMessage: action.errorMessage,
            }

        default:
            return state
    }
}

export const getSearchInProgressId = (state) => getSearchStatus(state).inProgress;
export const getSearchErrorMessage = (state) => getSearchStatus(state).errorMessage;
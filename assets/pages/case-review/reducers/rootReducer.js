import { combineReducers } from 'redux'

const rootReducer = (state = {
    'user' : {},
    'project': {},
    'families_by_id': {},
    'individuals_by_id': {},
    'family_id_to_indiv_ids': {},
}, action) => {
    console.log(action, state)
    return state
}


    //combineReducers({
    //families_and_individuals,
//});


export default rootReducer;


// selectors
export const getProject = (state) => state.project
/*
export const getSearchStatus = (state) => state.searchStatus
export const getSearchResults = (state) => state.searchResults
*/
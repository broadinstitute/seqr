
// actions
export const SET_SEARCH_RESULT = 'SET_SEARCH_RESULT'


// action creators
export const setSearchResults = (results) => {
  return {
    type: SET_SEARCH_RESULT,
    results: results,
  }
}

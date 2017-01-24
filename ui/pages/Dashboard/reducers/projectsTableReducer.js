import { SHOW_ALL, SORT_BY_PROJECT_NAME } from '../constants'

// actions
const UPDATE_FILTER = 'UPDATE_FILTER'
const UPDATE_SORT_ORDER = 'UPDATE_SORT_ORDER'
const UPDATE_SORT_DIRECTION = 'UPDATE_SORT_DIRECTION'
const UPDATE_SHOW_CATEGORIES = 'UPDATE_SHOW_CATEGORIES'


// action creators
export const updateFilter = filter => ({ type: UPDATE_FILTER, newState: { filter } })
export const updateSortColumn = sortColumn => ({ type: UPDATE_SORT_ORDER, newState: { sortColumn } })
export const updateSortDirection = sortDirection => ({ type: UPDATE_SORT_DIRECTION, newState: { sortDirection } })
export const updateShowCategories = showCategories => ({ type: UPDATE_SHOW_CATEGORIES, newState: { showCategories } })

// reducers
const projectsTableReducer = (state = {
  filter: SHOW_ALL,
  sortColumn: SORT_BY_PROJECT_NAME,
  sortDirection: 1,
  showCategories: true,
}, action) => {
  switch (action.type) {
    case UPDATE_FILTER:
    case UPDATE_SORT_ORDER:
    case UPDATE_SORT_DIRECTION:
    case UPDATE_SHOW_CATEGORIES:
      return { ...state, ...action.newState }
    default:
      return state
  }
}

export default projectsTableReducer

import { SHOW_ALL, SORT_BY_PROJECT_NAME } from '../constants'


// actions
const UPDATE_FILTER = 'UPDATE_FILTER'
const UPDATE_SORT_ORDER = 'UPDATE_SORT_ORDER'
const UPDATE_SORT_DIRECTION = 'UPDATE_SORT_DIRECTION'
const UPDATE_SHOW_DETAILS = 'UPDATE_SHOW_DETAILS'

// action creators
export const updateFilter = filter => ({ type: UPDATE_FILTER, newState: { filter } })
export const updateSortOrder = sortOrder => ({ type: UPDATE_SORT_ORDER, newState: { sortOrder } })
export const updateSortDirection = sortDirection => ({ type: UPDATE_SORT_DIRECTION, newState: { sortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_SHOW_DETAILS, newState: { showDetails } })

// reducers
const projectsTableReducer = (state = {
  filter: SHOW_ALL,
  sortOrder: SORT_BY_PROJECT_NAME,
  sortDirection: 1,
  showDetails: true,
}, action) => {
  switch (action.type) {
    case UPDATE_FILTER:
    case UPDATE_SORT_ORDER:
    case UPDATE_SORT_DIRECTION:
    case UPDATE_SHOW_DETAILS:
      return { ...state, ...action.newState }
    default:
      return state
  }
}

export default projectsTableReducer

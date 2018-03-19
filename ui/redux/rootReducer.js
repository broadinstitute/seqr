import { combineReducers } from 'redux'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { zeroActionsReducer, createSingleObjectReducer, createObjectsByIdReducer } from './utils/reducerUtils'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const UPDATE_MODAL_DIALOG_STATE = 'UPDATE_MODAL_DIALOG_STATE'
const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
const RECEIVE_PROJECTS = 'RECEIVE_PROJECTS'
const UPDATE_PROJECTS_BY_GUID = 'UPDATE_PROJECTS_BY_GUID'
const UPDATE_PROJECT_CATEGORIES_BY_GUID = 'UPDATE_PROJECT_CATEGORIES_BY_GUID'

// action creators
export const showModal = (modalType, modalProjectGuid) => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updates: { modalIsVisible: true, modalType, modalProjectGuid } })

export const hideModal = () => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updates: { modalIsVisible: false, modalType: null } })

export const updateProjectsByGuid = projectsByGuid => ({ type: UPDATE_PROJECTS_BY_GUID, updatesById: projectsByGuid })

export const updateProjectCategoriesByGuid = projectCategoriesByGuid => ({
  type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: projectCategoriesByGuid,
})

//TODO cleanup
export const fetchProjects = () => {
  return (dispatch, getState) => {
    if (!(getState().projects && getState().projects.allLoaded)) {
      dispatch({ type: REQUEST_PROJECTS })
      new HttpRequestHelper('/api/dashboard',
        (responseJson) => {
          // TODO single action?
          dispatch({ type: UPDATE_PROJECTS_BY_GUID, updatesById: responseJson.projectsByGuid })
          dispatch({ type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: responseJson.projectCategoriesByGuid })
          dispatch({ type: RECEIVE_PROJECTS, success: true })
        },
        () => dispatch({ type: RECEIVE_PROJECTS, success: false }),
      ).get()
    }
  }
}

function fetchProjectsReducer(state = {}, action) {
  switch (action.type) {
    case REQUEST_PROJECTS:
      return Object.assign({}, state, {
        loading: true,
      })
    case RECEIVE_PROJECTS:
      return Object.assign({}, state, {
        loading: false, allLoaded: action.success,
      })
    default:
      return state
  }
}

// root reducer
const rootReducer = combineReducers(Object.assign({
  modalDialogState: createSingleObjectReducer(UPDATE_MODAL_DIALOG_STATE, {
    modalIsVisible: false, modalType: null, modalProjectGuid: null }, true),
  projectsByGuid: createObjectsByIdReducer(UPDATE_PROJECTS_BY_GUID, {}, false),
  projectCategoriesByGuid: createObjectsByIdReducer(UPDATE_PROJECT_CATEGORIES_BY_GUID, {}, false),
  projects: fetchProjectsReducer,
  user: zeroActionsReducer,
}, dashboardReducers))

export default rootReducer

// basic selectors
export const getModalDialogState = state => state.modalDialogState
export const projectsLoading = state => Boolean(state.projects.loading)
export const getProjectsByGuid = state => state.projectsByGuid // TODO nest this in main projects object
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getUser = state => state.user

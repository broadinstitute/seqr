import { combineReducers } from 'redux'
import { reducer as formReducer, SubmissionError } from 'redux-form'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { createSingleObjectReducer, createObjectsByIdReducer, fetchObjectsReducer } from './utils/reducerUtils'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const UPDATE_MODAL_DIALOG_STATE = 'UPDATE_MODAL_DIALOG_STATE'
const UPDATE_USER = 'UPDATE_USER'
const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
const RECEIVE_PROJECTS = 'RECEIVE_PROJECTS'
const UPDATE_PROJECTS_BY_GUID = 'UPDATE_PROJECTS_BY_GUID'
const UPDATE_PROJECT_CATEGORIES_BY_GUID = 'UPDATE_PROJECT_CATEGORIES_BY_GUID'

// action creator
// TODO deprecate global modals and remove these
export const showModal = (modalType, modalProjectGuid) => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updates: { modalIsVisible: true, modalType, modalProjectGuid } })

export const hideModal = () => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updates: { modalIsVisible: false, modalType: null } })

// TODO this doesnt work get rid of it
export const updateProjectsByGuid = projectsByGuid => ({ type: UPDATE_PROJECTS_BY_GUID, updatesById: projectsByGuid })

export const updateProjectCategoriesByGuid = projectCategoriesByGuid => ({
  type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: projectCategoriesByGuid,
})

export const fetchProjects = () => {
  return (dispatch, getState) => {
    if (!getState().projects.allLoaded) {
      dispatch({ type: REQUEST_PROJECTS })
      new HttpRequestHelper('/api/dashboard',
        (responseJson) => {
          dispatch({ type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: responseJson.projectCategoriesByGuid })
          dispatch({ type: UPDATE_USER, updates: responseJson.user })
          dispatch({ type: RECEIVE_PROJECTS, allLoaded: true, byGuid: responseJson.projectsByGuid })
        },
        () => dispatch({ type: RECEIVE_PROJECTS, allLoaded: false, byGuid: {} }),
      ).get()
    }
  }
}

export const updateProject = (values) => {
  return (dispatch) => {
    const urlPath = values.projectGuid ? `/api/project/${values.projectGuid}` : '/api/project'
    let action = 'create'
    if (values.projectGuid) {
      action = values.delete ? 'delete' : 'update'
    }
    return new HttpRequestHelper(`${urlPath}/${action}_project`,
      (responseJson) => {
        dispatch({ type: RECEIVE_PROJECTS, byGuid: responseJson.projectsByGuid })
      },
      (e) => { throw new SubmissionError({ _error: e.message }) },
    ).post(values)
  }
}

// root reducer
const rootReducer = combineReducers(Object.assign({
  modalDialogState: createSingleObjectReducer(UPDATE_MODAL_DIALOG_STATE, {
    modalIsVisible: false, modalType: null, modalProjectGuid: null }),
  projectCategoriesByGuid: createObjectsByIdReducer(UPDATE_PROJECT_CATEGORIES_BY_GUID),
  projects: fetchObjectsReducer(REQUEST_PROJECTS, RECEIVE_PROJECTS),
  user: createSingleObjectReducer(UPDATE_USER),
  form: formReducer,
}, dashboardReducers))

export default rootReducer

// basic selectors
export const getModalDialogState = state => state.modalDialogState
export const projectsLoading = state => state.projects.loading
export const getProjectsByGuid = state => state.projects.byGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getUser = state => state.user

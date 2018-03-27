import { combineReducers } from 'redux'
import { reducer as formReducer, SubmissionError } from 'redux-form'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { createObjectsByIdReducer, loadingReducer, zeroActionsReducer, createSingleValueReducer } from './utils/reducerFactories'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
const RECEIVE_PROJECTS = 'RECEIVE_PROJECTS'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const UPDATE_PROJECT_CATEGORIES_BY_GUID = 'UPDATE_PROJECT_CATEGORIES_BY_GUID'

// action creators
export const fetchProjects = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_PROJECTS })
    new HttpRequestHelper('/api/dashboard',
      (responseJson) => {
        dispatch({ type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: responseJson.projectCategoriesByGuid })
        dispatch({ type: RECEIVE_PROJECTS, updatesById: responseJson.projectsByGuid })
      },
      e => dispatch({ type: RECEIVE_PROJECTS, error: e.message, updatesById: {} }),
    ).get()
  }
}

export const loadProject = (projectGuid) => {
  return (dispatch, getState) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: projectGuid })
    if (!getState().projectsByGuid[projectGuid]) {
      dispatch({ type: REQUEST_PROJECTS })
      // TODO actually fetch the right project
      new HttpRequestHelper('/api/dashboard',
        (responseJson) => {
          dispatch({ type: RECEIVE_PROJECTS, updatesById: responseJson.projectsByGuid })
        },
        e => dispatch({ type: RECEIVE_PROJECTS, error: e.message, updatesById: {} }),
      ).get()
    }
  }
}

export const updateProject = (values) => {
  return (dispatch) => {
    const urlPath = values.projectGuid ? `/api/project/${values.projectGuid}` : '/api/project'
    const projectField = values.projectField ? `_${values.projectField}` : ''
    let action = 'create'
    if (values.projectGuid) {
      action = values.delete ? 'delete' : 'update'
    }

    return new HttpRequestHelper(`${urlPath}/${action}_project${projectField}`,
      (responseJson) => {
        if (responseJson.projectCategoriesByGuid) {
          dispatch({ type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: responseJson.projectCategoriesByGuid })
        }
        dispatch({ type: RECEIVE_PROJECTS, updatesById: responseJson.projectsByGuid })
      },
      (e) => { throw new SubmissionError({ _error: e.message }) },
    ).post(values)
  }
}

// root reducer
const rootReducer = combineReducers(Object.assign({
  projectCategoriesByGuid: createObjectsByIdReducer(UPDATE_PROJECT_CATEGORIES_BY_GUID),
  projectsByGuid: createObjectsByIdReducer(RECEIVE_PROJECTS),
  projectsLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_PROJECTS),
  currentProjectGuid: createSingleValueReducer(UPDATE_CURRENT_PROJECT, null),
  user: zeroActionsReducer,
  form: formReducer,
}, dashboardReducers))

export default rootReducer

// basic selectors
export const projectsLoading = state => state.projectsLoading.loading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getProject = state => state.projectsByGuid[state.currentProjectGuid]
export const getUser = state => state.user

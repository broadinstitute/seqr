import { combineReducers } from 'redux'
import { reducer as formReducer, SubmissionError } from 'redux-form'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { reducers as projectReducers } from 'pages/Project/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { createObjectsByIdReducer, loadingReducer, zeroActionsReducer, createSingleValueReducer } from './utils/reducerFactories'
import modalReducers from './utils/modalReducer'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const RECEIVE_DATA = 'RECEIVE_DATA'
const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'


// action creators
export const fetchProjects = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_PROJECTS })
    new HttpRequestHelper('/api/dashboard',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      e => dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} }),
    ).get()
  }
}

export const loadProject = (projectGuid) => {
  return (dispatch, getState) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: projectGuid })

    const currentProject = getState().projectsByGuid[projectGuid]
    if (!currentProject || !currentProject.detailsLoaded) {
      dispatch({ type: REQUEST_PROJECT_DETAILS })
      if (!currentProject) {
        dispatch({ type: REQUEST_PROJECTS })
      }
      new HttpRequestHelper(`/api/project/${projectGuid}/details`,
        (responseJson) => {
          dispatch({ type: RECEIVE_DATA, updatesById: { projectsByGuid: { [projectGuid]: responseJson.project }, ...responseJson } })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).get()
    }
  }
}

export const unloadProject = () => {
  return (dispatch) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: null })
  }
}

/**
 * POSTS a request to update the specified project and dispatches the appropriate events when the request finishes
 * Accepts a values object that includes any data to be posted as well as the following keys:
 *
 * action: A string representation of the action to perform. Can be "create", "update" or "delete". Defaults to "update"
 * projectGuid: The GUID for the project to update. If omitted, the action will be set to "create"
 * projectField: A specific field to update (e.g. "categories"). Should be used for fields which have special server-side logic for updating
 */
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
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => { throw new SubmissionError({ _error: [e.message] }) },
    ).post(values)
  }
}

export const updateFamilies = (values) => {
  return (dispatch, getState) => {
    const action = values.delete ? 'delete' : 'edit'
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/${action}_families`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => { throw new SubmissionError({ _error: [e.message] }) },
    ).post(values)
  }
}

export const updateIndividuals = (values) => {
  return (dispatch, getState) => {
    let action = 'edit_individuals'
    if (values.uploadedFileId) {
      action = `save_individuals_table/${values.uploadedFileId}`
    } else if (values.delete) {
      action = 'delete_individuals'
    }

    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/${action}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        if (e.body && e.body.errors) {
          throw new SubmissionError({ _error: e.body.errors })
          // e.body.warnings.forEach((err) => { throw new SubmissionError({ _warning: err }) })
        } else {
          throw new SubmissionError({ _error: [e.message] })
        }
      },
    ).post(values)
  }
}

export const updateIndividual = (individualGuid, values) => {
  return (dispatch) => {
    return new HttpRequestHelper(`/api/individual/${individualGuid}/update`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: { individualsByGuid: responseJson } })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}


// root reducer
const rootReducer = combineReducers(Object.assign({
  projectCategoriesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectCategoriesByGuid'),
  projectsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectsByGuid'),
  projectsLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_DATA),
  currentProjectGuid: createSingleValueReducer(UPDATE_CURRENT_PROJECT, null),
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_DATA),
  familiesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'familiesByGuid'),
  individualsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'individualsByGuid'),
  datasetsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'datasetsByGuid'),
  samplesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'samplesByGuid'),
  user: zeroActionsReducer,
  form: formReducer,
}, modalReducers, dashboardReducers, projectReducers))

export default rootReducer

// basic selectors
export const getProjectsIsLoading = state => state.projectsLoading.isLoading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getProject = state => state.projectsByGuid[state.currentProjectGuid]
export const getProjectDetailsIsLoading = state => state.projectDetailsLoading.isLoading
export const getProjectFamilies = state => Object.values(state.familiesByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectIndividuals = state => Object.values(state.individualsByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectIndividualsWithFamily = state =>
  getProjectIndividuals(state).map((ind) => { return { family: state.familiesByGuid[ind.familyGuid], ...ind } })
export const getProjectDatasets = state => Object.values(state.datasetsByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectSamples = state => Object.values(state.samplesByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getUser = state => state.user

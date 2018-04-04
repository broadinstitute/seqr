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
const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
const RECEIVE_PROJECTS = 'RECEIVE_PROJECTS'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const UPDATE_PROJECT_CATEGORIES_BY_GUID = 'UPDATE_PROJECT_CATEGORIES_BY_GUID'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
const RECEIVE_PROJECT_DETAILS = 'RECEIVE_PROJECT_DETAILS'
const RECEIVE_FAMILIES = 'RECEIVE_FAMILIES'
const RECEIVE_INDIVIDUALS = 'RECEIVE_INDIVIDUALS'
const RECEIVE_SAMPLES = 'RECEIVE_SAMPLES'
const RECEIVE_DATASETS = 'RECEIVE_DATASETS'

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

    const currentProject = getState().projectsByGuid[projectGuid]
    if (!currentProject || !currentProject.detailsLoaded) {
      dispatch({ type: REQUEST_PROJECT_DETAILS })
      if (!currentProject) {
        dispatch({ type: REQUEST_PROJECTS })
      }
      new HttpRequestHelper(`/api/project/${projectGuid}/details`,
        (responseJson) => {
          dispatch({ type: RECEIVE_PROJECT_DETAILS })
          dispatch({ type: RECEIVE_PROJECTS, updatesById: { [projectGuid]: responseJson.project } })
          dispatch({ type: RECEIVE_FAMILIES, updatesById: responseJson.familiesByGuid })
          dispatch({ type: RECEIVE_INDIVIDUALS, updatesById: responseJson.individualsByGuid })
          dispatch({ type: RECEIVE_SAMPLES, updatesById: responseJson.samplesByGuid })
          dispatch({ type: RECEIVE_DATASETS, updatesById: responseJson.datasetsByGuid })
        },
        (e) => {
          dispatch({ type: RECEIVE_PROJECT_DETAILS, error: e.message })
          dispatch({ type: RECEIVE_PROJECTS, error: e.message, updatesById: {} })
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
      (e) => { throw new SubmissionError({ _error: [e.message] }) },
    ).post(values)
  }
}

export const updateFamilies = (values) => {
  return (dispatch, getState) => {
    const action = values.delete ? 'delete' : 'edit'
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/${action}_families`,
      (responseJson) => {
        dispatch({ type: RECEIVE_FAMILIES, updatesById: responseJson.familiesByGuid })
      },
      (e) => { throw new SubmissionError({ _error: [e.message] }) },
    ).post(values)
  }
}

export const updateIndividuals = (values) => {
  return (dispatch, getState) => {
    const action = values.delete ? 'delete' : 'edit'
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/${action}_individuals`,
      (responseJson) => {
        dispatch({ type: RECEIVE_INDIVIDUALS, updatesById: responseJson.individualsByGuid })
        dispatch({ type: RECEIVE_FAMILIES, updatesById: responseJson.familiesByGuid })
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


// root reducer
const rootReducer = combineReducers(Object.assign({
  projectCategoriesByGuid: createObjectsByIdReducer(UPDATE_PROJECT_CATEGORIES_BY_GUID),
  projectsByGuid: createObjectsByIdReducer(RECEIVE_PROJECTS),
  projectsLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_PROJECTS),
  currentProjectGuid: createSingleValueReducer(UPDATE_CURRENT_PROJECT, null),
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_PROJECT_DETAILS),
  familiesByGuid: createObjectsByIdReducer(RECEIVE_FAMILIES),
  individualsByGuid: createObjectsByIdReducer(RECEIVE_INDIVIDUALS),
  datasetsByGuid: createObjectsByIdReducer(RECEIVE_DATASETS),
  samplesByGuid: createObjectsByIdReducer(RECEIVE_SAMPLES),
  user: zeroActionsReducer,
  form: formReducer,
}, modalReducers, dashboardReducers, projectReducers))

export default rootReducer

// basic selectors
export const projectsLoading = state => state.projectsLoading.loading
export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getProject = state => state.projectsByGuid[state.currentProjectGuid]
export const projectDetailsLoading = state => state.projectDetailsLoading.loading
export const getProjectFamilies = state => Object.values(state.familiesByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectIndividuals = state => Object.values(state.individualsByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectIndividualsWithFamily = state =>
  getProjectIndividuals(state).map((ind) => { return { family: state.familiesByGuid[ind.familyGuid], ...ind } })
export const getProjectDatasets = state => Object.values(state.datasetsByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectSamples = state => Object.values(state.samplesByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getUser = state => state.user

import { combineReducers } from 'redux'

import { loadingReducer, createSingleObjectReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import {
  REQUEST_PROJECTS, RECEIVE_PROJECTS, RECEIVE_FAMILIES, RECEIVE_INDIVIDUALS, RECEIVE_SAMPLES, RECEIVE_DATASETS,
} from 'redux/rootReducer'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SHOW_ALL, SORT_BY_FAMILY_NAME } from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const UPDATE_FAMILY_TABLE_STATE = 'UPDATE_FAMILY_TABLE_STATE'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
const RECEIVE_PROJECT_DETAILS = 'RECEIVE_PROJECT_DETAILS'
const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
const RECEIVE_SAVED_VARIANTS = 'RECEIVE_SAVED_VARIANTS'

// Data selectors
export const getProject = state => state.projectsByGuid[state.currentProjectGuid]
export const getProjectDetailsIsLoading = state => state.projectDetailsLoading.isLoading
export const getProjectSavedVariantsIsLoading = state => state.projectSavedVariantsLoading.isLoading
export const getProjectSavedVariants = (state, tag) => {
  return tag ? state.projectSavedVariants.filter(o => o.tags.includes(tag)) : state.projectSavedVariants }
export const getProjectFamilies = state => Object.values(state.familiesByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectIndividuals = state => Object.values(state.individualsByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectIndividualsWithFamily = state =>
  getProjectIndividuals(state).map((ind) => { return { family: state.familiesByGuid[ind.familyGuid], ...ind } })
export const getProjectDatasets = state => Object.values(state.datasetsByGuid).filter(o => o.projectGuid === state.currentProjectGuid)
export const getProjectSamples = state => Object.values(state.samplesByGuid).filter(o => o.projectGuid === state.currentProjectGuid)

// Family table selectors
export const getProjectTableState = state => state.familyTableState
export const getProjectTablePage = state => state.familyTableState.currentPage || 1
export const getProjectTableRecordsPerPage = state => state.familyTableState.recordsPerPage || 200
export const getFamiliesFilter = state => state.familyTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.familyTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.familyTableState.familiesSortDirection || 1
export const getShowDetails = state => (state.familyTableState.showDetails !== undefined ? state.familyTableState.showDetails : true)

// Data actions

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

export const loadProjectVariants = (tag) => {
  return (dispatch, getState) => {
    const state = getState()
    const project = getProject(state)
    let tagTypes = project.variantTagTypes.filter(vtt => vtt.numTags > 0)
    if (tag) {
      tagTypes = tagTypes.filter(vtt => vtt.name === tag)
    }
    if (tagTypes.some(vtt => getProjectSavedVariants(state, vtt.name).length !== vtt.numTags)) {
      dispatch({ type: REQUEST_SAVED_VARIANTS })
      const tagPath = tag ? `/${tag}` : ''
      new HttpRequestHelper(`/api/project/${project.projectGuid}/saved_variants${tagPath}`,
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_VARIANTS, newValue: responseJson.savedVariants })
        },
        (e) => {
          dispatch({ type: RECEIVE_SAVED_VARIANTS, error: e.message, newValue: [] })
        },
      ).get()
    }
  }
}

export const unloadProject = () => {
  return (dispatch) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: null })
    dispatch({ type: RECEIVE_SAVED_VARIANTS, newValue: [] })
  }
}

// Family table actions

export const setCurrentPage = currentPage => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { currentPage } })
export const setRecordsPerPage = recordsPerPage => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { recordsPerPage } })

export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { showDetails } })

// reducers

export const reducers = {
  currentProjectGuid: createSingleValueReducer(UPDATE_CURRENT_PROJECT, null),
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_PROJECT_DETAILS),
  projectSavedVariants: createSingleValueReducer(RECEIVE_SAVED_VARIANTS, []),
  projectSavedVariantsLoading: loadingReducer(REQUEST_SAVED_VARIANTS, RECEIVE_SAVED_VARIANTS),
  familyTableState: createSingleObjectReducer(UPDATE_FAMILY_TABLE_STATE, {
    currentPage: 1,
    recordsPerPage: 200,
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

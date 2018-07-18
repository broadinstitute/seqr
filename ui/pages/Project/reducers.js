import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import { loadingReducer, createSingleObjectReducer, createObjectsByIdReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { REQUEST_PROJECTS, RECEIVE_DATA } from 'redux/rootReducer'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { getProject, getProjectFamiliesByGuid } from 'pages/Project/selectors'
import {
  SHOW_ALL, SHOW_IN_REVIEW, SORT_BY_FAMILY_NAME, SORT_BY_FAMILY_ADDED_DATE, SORT_BY_FAMILY_GUID, CASE_REVIEW_TABLE_NAME,
} from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const UPDATE_FAMILY_TABLE_STATE = 'UPDATE_FAMILY_TABLE_STATE'
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'
const UPDATE_SAVED_VARIANT_TABLE_STATE = 'UPDATE_VARIANT_STATE'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
const RECEIVE_PROJECT_DETAILS = 'RECEIVE_PROJECT_DETAILS'
const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
const RECEIVE_SAVED_VARIANTS = 'RECEIVE_SAVED_VARIANTS'
const RECEIVE_SAVED_VARIANT_FAMILIES = 'RECEIVE_SAVED_VARIANT_FAMILIES'

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
          dispatch({ type: RECEIVE_DATA, updatesById: { projectsByGuid: { [projectGuid]: responseJson.project }, ...responseJson } })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).get()
    }
  }
}

export const loadProjectVariants = (familyGuid, variantGuid) => {
  return (dispatch, getState) => {
    const state = getState()
    const project = getProject(state)

    let url = `/api/project/${project.projectGuid}/saved_variants`

    // Do not load if already loaded
    let expectedFamilyGuids
    if (variantGuid) {
      if (state.projectSavedVariants[variantGuid]) {
        return
      }
      url = `${url}/${variantGuid}`
    } else {
      expectedFamilyGuids = familyGuid ? [familyGuid] : Object.keys(getProjectFamiliesByGuid(state))
      if (expectedFamilyGuids.length > 0 && expectedFamilyGuids.every(family => state.projectSavedVariantFamilies[family])) {
        return
      }
    }

    dispatch({ type: REQUEST_SAVED_VARIANTS })
    new HttpRequestHelper(url,
      (responseJson) => {
        dispatch({ type: RECEIVE_SAVED_VARIANTS, updatesById: responseJson.savedVariants })
        if (expectedFamilyGuids) {
          dispatch({
            type: RECEIVE_SAVED_VARIANT_FAMILIES,
            updates: expectedFamilyGuids.reduce((acc, family) => ({ ...acc, [family]: true }), {}),
          })
        }
      },
      (e) => {
        dispatch({ type: RECEIVE_SAVED_VARIANTS, error: e.message, updatesById: {} })
      },
    ).get(familyGuid ? { family: familyGuid } : {})
  }
}

export const unloadProject = () => {
  return (dispatch, getState) => {
    const state = getState()
    const variantsToDelete = Object.keys(state.projectSavedVariants).reduce((acc, o) => ({ ...acc, [o]: null }), {})
    const variantFamiliesToDelete = Object.keys(state.projectSavedVariantFamilies).reduce((acc, o) => ({ ...acc, [o]: false }), {})
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: null })
    dispatch({ type: REQUEST_SAVED_VARIANTS, updatesById: variantsToDelete })
    dispatch({ type: RECEIVE_SAVED_VARIANT_FAMILIES, updates: variantFamiliesToDelete })
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

export const addDataset = (values) => {
  return (dispatch, getState) => {
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/add_dataset`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        if (e.body && e.body.errors) {
          throw new SubmissionError({ _error: e.body.errors })
        } else {
          throw new SubmissionError({ _error: [e.message] })
        }
      },
    ).post(values)
  }
}

// Table actions
export const updateFamiliesTable = (updates, tableName) => (
  { type: tableName === CASE_REVIEW_TABLE_NAME ? UPDATE_CASE_REVIEW_TABLE_STATE : UPDATE_FAMILY_TABLE_STATE, updates }
)
export const updateSavedVariantTable = updates => ({ type: UPDATE_SAVED_VARIANT_TABLE_STATE, updates })

// reducers

export const reducers = {
  currentProjectGuid: createSingleValueReducer(UPDATE_CURRENT_PROJECT, null),
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_PROJECT_DETAILS),
  projectSavedVariants: createObjectsByIdReducer(RECEIVE_SAVED_VARIANTS),
  projectSavedVariantsLoading: loadingReducer(REQUEST_SAVED_VARIANTS, RECEIVE_SAVED_VARIANTS),
  projectSavedVariantFamilies: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_FAMILIES),
  familyTableState: createSingleObjectReducer(UPDATE_FAMILY_TABLE_STATE, {
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
  }, false),
  caseReviewTableState: createSingleObjectReducer(UPDATE_CASE_REVIEW_TABLE_STATE, {
    familiesFilter: SHOW_IN_REVIEW,
    familiesSortOrder: SORT_BY_FAMILY_ADDED_DATE,
    familiesSortDirection: 1,
  }, false),
  savedVariantTableState: createSingleObjectReducer(UPDATE_SAVED_VARIANT_TABLE_STATE, {
    hideExcluded: false,
    categoryFilter: SHOW_ALL,
    sortOrder: SORT_BY_FAMILY_GUID,
    currentPage: 1,
    recordsPerPage: 25,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

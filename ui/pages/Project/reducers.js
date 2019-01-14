import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import { loadingReducer, createSingleObjectReducer, createSingleValueReducer } from 'redux/utils/reducerFactories'
import { updateEntity, loadProject } from 'redux/rootReducer'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SORT_BY_FAMILY_GUID } from 'shared/utils/constants'
import { getProject, getProjectFamiliesByGuid } from 'pages/Project/selectors'
import {
  SHOW_ALL, SHOW_IN_REVIEW, SORT_BY_FAMILY_NAME, SORT_BY_FAMILY_ADDED_DATE, CASE_REVIEW_TABLE_NAME,
} from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const RECEIVE_DATA = 'RECEIVE_DATA'
const UPDATE_FAMILY_TABLE_STATE = 'UPDATE_FAMILY_TABLE_STATE'
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'
const UPDATE_SAVED_VARIANT_TABLE_STATE = 'UPDATE_VARIANT_STATE'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
const RECEIVE_SAVED_VARIANT_FAMILIES = 'RECEIVE_SAVED_VARIANT_FAMILIES'
const REQUEST_MME_MATCHES = 'REQUEST_MME_MATCHES'
const REQUEST_MONARCH_MATCHES = 'REQUEST_MONARCH_MATCHES'


// Data actions

export const loadCurrentProject = (projectGuid) => {
  return (dispatch) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: projectGuid })
    dispatch(loadProject(projectGuid))
  }
}

export const loadProjectVariants = (familyGuids, variantGuid) => {
  return (dispatch, getState) => {
    const state = getState()
    const project = getProject(state)

    let url = `/api/project/${project.projectGuid}/saved_variants`

    // Do not load if already loaded
    let expectedFamilyGuids
    if (variantGuid) {
      if (state.savedVariantsByGuid[variantGuid]) {
        return
      }
      url = `${url}/${variantGuid}`
    } else {
      expectedFamilyGuids = familyGuids || Object.keys(getProjectFamiliesByGuid(state))
      if (expectedFamilyGuids.length > 0 && expectedFamilyGuids.every(family => state.projectSavedVariantFamilies[family])) {
        return
      }
    }

    dispatch({ type: REQUEST_SAVED_VARIANTS })
    new HttpRequestHelper(url,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        if (expectedFamilyGuids) {
          dispatch({
            type: RECEIVE_SAVED_VARIANT_FAMILIES,
            updates: expectedFamilyGuids.reduce((acc, family) => ({ ...acc, [family]: true }), {}),
          })
        }
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      },
    ).get(familyGuids ? { families: familyGuids.join(',') } : {})
  }
}

const unloadSavedVariants = (dispatch, getState) => {
  const state = getState()
  const variantsToDelete = Object.keys(state.projectSavedVariants || {}).reduce((acc, o) => ({ ...acc, [o]: null }), {})
  const variantFamiliesToDelete = Object.keys(state.projectSavedVariantFamilies).reduce((acc, o) => ({ ...acc, [o]: false }), {})
  dispatch({ type: RECEIVE_DATA, updatesById: { savedVariantsByGuid: variantsToDelete } })
  dispatch({ type: RECEIVE_SAVED_VARIANT_FAMILIES, updates: variantFamiliesToDelete })
}

export const unloadProject = () => {
  return (dispatch) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: null })
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

export const updateIndividualsHpoTerms = ({ updatesByIndividualGuid }) => {
  return (dispatch, getState) => {
    const errors = []

    return Promise.all(Object.entries(updatesByIndividualGuid).map(([individualGuid, values]) =>
      new HttpRequestHelper(`/api/individual/${individualGuid}/update_hpo_terms`,
        responseJson => dispatch({ type: RECEIVE_DATA, updatesById: { [individualGuid]: responseJson } }),
        e => errors.push(`Error updating ${getState().individualsByGuid[individualGuid].individualId}: ${e.message}`),
      ).post(values),
    )).then(() => {
      if (errors.length) {
        throw new SubmissionError({ _error: errors })
      }
    })
  }
}

export const addDataset = (values) => {
  return (dispatch, getState) => {
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/add_dataset`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })

        // Clear all loaded variants and update the saved variant json. This should happen asynchronously
        unloadSavedVariants(dispatch, getState)
        new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/update_saved_variant_json`).get()

        window.location.href = window.location.href //TODO remove this - reload the page to apply dataset changes
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

export const updateLocusLists = (values) => {
  return (dispatch, getState) => {
    const projectGuid = getState().currentProjectGuid
    const action = values.delete ? 'delete' : 'add'
    return new HttpRequestHelper(`/api/project/${projectGuid}/${action}_locus_lists`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: { projectsByGuid: { [projectGuid]: responseJson } } })
      },
      (e) => { throw new SubmissionError({ _error: [e.message] }) },
    ).post(values)
  }
}

export const updateAnalysisGroup = (values) => {
  return updateEntity(values, RECEIVE_DATA, `/api/project/${values.projectGuid}/analysis_groups`, 'analysisGroupGuid')
}

export const loadMmeMatches = (submission, matchSource) => {
  return (dispatch, getState) => {
    const state = getState()
    const currentProject = state.projectsByGuid[state.currentProjectGuid]
    const individualSubmission = state.matchmakerSubmissions[currentProject.projectGuid][submission.individualId]
    const matchKey = `${matchSource || 'mme'}Match`
    if (!individualSubmission || !individualSubmission[matchKey]) {
      dispatch({ type: matchSource === 'monarch' ? REQUEST_MONARCH_MATCHES : REQUEST_MME_MATCHES })
      const searchPath = matchSource === 'monarch' ? 'match_in_open_mme_sources' : 'match_internally_and_externally'
      new HttpRequestHelper(`/api/matchmaker/${searchPath}/project/${currentProject.deprecatedProjectId}/individual/${submission.individualId}`,
        (responseJson) => {
          dispatch({
            type: RECEIVE_DATA,
            updatesById: {
              matchmakerSubmissions: {
                [currentProject.projectGuid]: {
                  [submission.individualId]: { ...individualSubmission, [matchKey]: responseJson },
                },
              },
            },
          })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).postForm({ patient_data: submission.submittedData })
    }
  }
}

export const deleteMmePatient = (individual) => {
  return (dispatch, getState) => {
    const state = getState()
    const currentProject = state.projectsByGuid[state.currentProjectGuid]
    return new HttpRequestHelper(
      `/api/matchmaker/project/${currentProject.deprecatedProjectId}/individual/${individual.individualId}/delete`,
      () => {},
      (e) => { throw e },
    ).get()
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
  projectSavedVariantsLoading: loadingReducer(REQUEST_SAVED_VARIANTS, RECEIVE_DATA),
  projectSavedVariantFamilies: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_FAMILIES),
  matchmakerMatchesLoading: loadingReducer(REQUEST_MME_MATCHES, RECEIVE_DATA),
  monarchMatchesLoading: loadingReducer(REQUEST_MONARCH_MATCHES, RECEIVE_DATA),
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
    hideReviewOnly: false,
    categoryFilter: SHOW_ALL,
    sort: SORT_BY_FAMILY_GUID,
    page: 1,
    recordsPerPage: 25,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

import { combineReducers } from 'redux'
import { SubmissionError } from 'redux-form'

import {
  loadingReducer, createSingleObjectReducer, createSingleValueReducer, createObjectsByIdReducer,
} from 'redux/utils/reducerFactories'
import { REQUEST_PROJECTS, REQUEST_SAVED_VARIANTS, updateEntity, loadProject } from 'redux/rootReducer'
import { SHOW_ALL, SORT_BY_FAMILY_GUID } from 'shared/utils/constants'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SHOW_IN_REVIEW, SORT_BY_FAMILY_NAME, SORT_BY_FAMILY_ADDED_DATE, CASE_REVIEW_TABLE_NAME } from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const RECEIVE_DATA = 'RECEIVE_DATA'
const UPDATE_FAMILY_TABLE_STATE = 'UPDATE_FAMILY_TABLE_STATE'
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
const RECEIVE_SAVED_VARIANT_FAMILIES = 'RECEIVE_SAVED_VARIANT_FAMILIES'
const UPDATE_SAVED_VARIANT_TABLE_STATE = 'UPDATE_VARIANT_STATE'
const REQUEST_MME_MATCHES = 'REQUEST_MME_MATCHES'


// Data actions

export const loadCurrentProject = (projectGuid) => {
  return (dispatch, getState) => {
    dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: projectGuid })
    const project = getState().projectsByGuid[projectGuid]
    if (!project) {
      dispatch({ type: REQUEST_PROJECTS })
    }
    return loadProject(projectGuid, REQUEST_PROJECT_DETAILS, 'detailsLoaded')(dispatch, getState)
  }
}

export const loadSavedVariants = ({ familyGuids, variantGuid }) => {
  return (dispatch, getState) => {
    const state = getState()
    const projectGuid = state.currentProjectGuid

    let url = `/api/project/${projectGuid}/saved_variants`

    // Do not load if already loaded
    let expectedFamilyGuids
    if (variantGuid) {
      if (state.savedVariantsByGuid[variantGuid]) {
        return
      }
      url = `${url}/${variantGuid}`
    } else {
      expectedFamilyGuids = familyGuids
      if (!expectedFamilyGuids) {
        expectedFamilyGuids = Object.values(state.familiesByGuid).filter(
          family => family.projectGuid === projectGuid).map(({ familyGuid }) => familyGuid)
      }
      if (expectedFamilyGuids.length > 0 && expectedFamilyGuids.every(family => state.savedVariantFamilies[family])) {
        return
      }
    }

    dispatch({ type: REQUEST_SAVED_VARIANTS })
    new HttpRequestHelper(url,
      (responseJson) => {
        if (expectedFamilyGuids) {
          dispatch({
            type: RECEIVE_SAVED_VARIANT_FAMILIES,
            updates: expectedFamilyGuids.reduce((acc, family) => ({ ...acc, [family]: true }), {}),
          })
        }
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      },
    ).get(familyGuids ? { families: familyGuids.join(',') } : {})
  }
}

export const loadFamilySavedVariants = familyGuid => loadSavedVariants({ familyGuids: [familyGuid] })

const unloadSavedVariants = (dispatch, getState) => {
  const state = getState()
  const variantsToDelete = Object.keys(state.savedVariantsByGuid).reduce((acc, o) => ({ ...acc, [o]: null }), {})
  const variantFamiliesToDelete = Object.keys(state.savedVariantFamilies).reduce((acc, o) => ({ ...acc, [o]: false }), {})
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

export const updateIndividualsHpoTerms = ({ uploadedFileId }) => {
  return (dispatch, getState) => {
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/save_hpo_terms_table/${uploadedFileId}`,
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
    ).post()
  }
}

export const addVariantsDataset = (values) => {
  return (dispatch, getState) => {
    return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/add_dataset/variants`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })

        // Clear all loaded variants and update the saved variant json. This should happen asynchronously
        unloadSavedVariants(dispatch, getState)
        new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/update_saved_variant_json`).post()
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

export const addIGVDataset = ({ mappingFile, ...values }) => {
  return (dispatch, getState) => {
    const errors = []

    return Promise.all(Object.entries(mappingFile.updatesByIndividualGuid).map(([individualGuid, filePath]) =>
      new HttpRequestHelper(`/api/individual/${individualGuid}/update_igv_sample`,
        responseJson => dispatch({ type: RECEIVE_DATA, updatesById: responseJson }),
        e => errors.push(`Error updating ${getState().individualsByGuid[individualGuid].individualId}: ${e.body && e.body.error ? e.body.error : e.message}`),
      ).post({ filePath, ...values }),
    )).then(() => {
      if (errors.length) {
        throw new SubmissionError({ _error: errors })
      }
    })
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

export const updateCollaborator = (values) => {
  return updateEntity(values, RECEIVE_DATA, null, 'username', null, state => `/api/project/${state.currentProjectGuid}/collaborators`)
}

export const updateAnalysisGroup = (values) => {
  return updateEntity(values, RECEIVE_DATA, `/api/project/${values.projectGuid}/analysis_groups`, 'analysisGroupGuid')
}

export const loadMmeMatches = (submissionGuid, search) => {
  return (dispatch, getState) => {
    const state = getState()
    const submission = state.mmeSubmissionsByGuid[submissionGuid]
    if (submission && (!submission.mmeResultGuids || search)) {
      const { familyGuid } = state.individualsByGuid[submission.individualGuid]
      dispatch({ type: REQUEST_MME_MATCHES })
      new HttpRequestHelper(`/api/matchmaker/${search ? 'search' : 'get'}_mme_matches/${submissionGuid}`,
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_VARIANT_FAMILIES, updates: { [familyGuid]: true } })
          dispatch({
            type: RECEIVE_DATA,
            updatesById: responseJson,
          })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).get()
    }
  }
}

export const updateMmeSubmission = (values) => {
  return updateEntity(values, RECEIVE_DATA, '/api/matchmaker/submission', 'submissionGuid')
}

export const updateMmeSubmissionStatus = (values) => {
  return updateEntity(values, RECEIVE_DATA, '/api/matchmaker/result_status', 'matchmakerResultGuid')
}

export const updateMmeContactNotes = (values) => {
  return updateEntity(values, RECEIVE_DATA, '/api/matchmaker/contact_notes', 'institution')
}

export const sendMmeContactEmail = (values) => {
  return (dispatch) => {
    return new HttpRequestHelper(`/api/matchmaker/send_email/${values.matchmakerResultGuid}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
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
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_DATA),
  matchmakerMatchesLoading: loadingReducer(REQUEST_MME_MATCHES, RECEIVE_DATA),
  mmeContactNotes: createObjectsByIdReducer(RECEIVE_DATA, 'mmeContactNotes'),
  savedVariantFamilies: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_FAMILIES),
  familyTableState: createSingleObjectReducer(UPDATE_FAMILY_TABLE_STATE, {
    familiesFilter: SHOW_ALL,
    familiesSearch: '',
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

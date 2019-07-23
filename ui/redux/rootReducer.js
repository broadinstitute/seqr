import { combineReducers } from 'redux'
import { reducer as formReducer, SubmissionError } from 'redux-form'
import { reducer as searchReducer } from 'redux-search'
import hash from 'object-hash'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { reducers as projectReducers } from 'pages/Project/reducers'
import { reducers as searchReducers } from 'pages/Search/reducers'
import { reducers as staffReducers } from 'pages/Staff/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SHOW_ALL, SORT_BY_FAMILY_GUID } from 'shared/utils/constants'
import {
  createObjectsByIdReducer, loadingReducer, zeroActionsReducer, createSingleObjectReducer, createSingleValueReducer,
} from './utils/reducerFactories'
import modalReducers from './utils/modalReducer'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
export const RECEIVE_DATA = 'RECEIVE_DATA'
export const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
export const RECEIVE_SAVED_SEARCHES = 'RECEIVE_SAVED_SEARCHES'
export const REQUEST_SAVED_SEARCHES = 'REQUEST_SAVED_SEARCHES'
const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
const RECEIVE_SAVED_VARIANT_FAMILIES = 'RECEIVE_SAVED_VARIANT_FAMILIES'
const REQUEST_GENES = 'REQUEST_GENES'
const REQUEST_GENE_LISTS = 'REQUEST_GENE_LISTS'
const REQUEST_GENE_LIST = 'REQUEST_GENE_LIST'
const UPDATE_SAVED_VARIANT_TABLE_STATE = 'UPDATE_VARIANT_STATE'
const UPDATE_IGV_VISIBILITY = 'UPDATE_IGV_VISIBILITY'
const REQUEST_USERS = 'REQUEST_USERS'
const RECEIVE_USERS = 'RECEIVE_USERS'

// action creators

// A helper action that handles create, update and delete requests
export const updateEntity = (values, receiveDataAction, urlPath, idField, actionSuffix, getUrlPath) => {
  return (dispatch, getState) => {
    if (getUrlPath) {
      urlPath = getUrlPath(getState())
    }

    let action = 'create'
    if (values[idField]) {
      urlPath = `${urlPath}/${values[idField]}`
      action = values.delete ? 'delete' : 'update'
    }

    return new HttpRequestHelper(`${urlPath}/${action}${actionSuffix || ''}`,
      (responseJson) => {
        dispatch({ type: receiveDataAction, updatesById: responseJson })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}


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

export const loadUserOptions = (staffOnly) => {

  return (dispatch) => {
    const url = staffOnly ? '/api/users/get_all_staff' : '/api/users/get_all'
    dispatch({ type: REQUEST_USERS })
    new HttpRequestHelper(url,
      (responseJson) => {
        dispatch({ type: RECEIVE_USERS, newValue: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_USERS, error: e.message, newValue: [] })
      },
    ).get()
  }
}

export const loadStaffOptions = () => loadUserOptions(true)

/**
 * POSTS a request to update the specified project and dispatches the appropriate events when the request finishes
 * Accepts a values object that includes any data to be posted as well as the following keys:
 *
 * action: A string representation of the action to perform. Can be "create", "update" or "delete". Defaults to "update"
 * projectGuid: The GUID for the project to update. If omitted, the action will be set to "create"
 * projectField: A specific field to update (e.g. "categories"). Should be used for fields which have special server-side logic for updating
 */
export const updateProject = (values) => {
  const actionSuffix = values.projectField ? `_project_${values.projectField}` : '_project'
  return updateEntity(values, RECEIVE_DATA, '/api/project', 'projectGuid', actionSuffix)
}

export const updateFamily = (values) => {
  return (dispatch) => {
    const familyField = values.familyField ? `_${values.familyField}` : ''
    return new HttpRequestHelper(`/api/family/${values.familyGuid}/update${familyField}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: { familiesByGuid: responseJson } })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}

export const updateIndividual = (values) => {
  return (dispatch) => {
    return new HttpRequestHelper(`/api/individual/${values.individualGuid}/update`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: { individualsByGuid: responseJson } })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}

export const loadGene = (geneId) => {
  return (dispatch, getState) => {
    const gene = getState().genesById[geneId]
    if (!gene || !gene.notes || !gene.expression) {
      dispatch({ type: REQUEST_GENES })
      new HttpRequestHelper(`/api/gene_info/${geneId}`,
        (responseJson) => {
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).get()
    }
  }
}

export const loadGenes = (geneIds) => {
  return (dispatch, getState) => {
    const state = getState()
    if ([...geneIds].some(geneId => !state.genesById[geneId])) {
      dispatch({ type: REQUEST_GENES })
      new HttpRequestHelper('/api/genes_info',
        (responseJson) => {
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        },
      ).get({ geneIds: [...geneIds] })
    }
  }
}

export const loadLocusLists = () => {
  return (dispatch) => {
    dispatch({ type: REQUEST_GENE_LISTS })
    new HttpRequestHelper('/api/locus_lists',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      },
    ).get()
  }
}

export const loadLocusListItems = (locusListId) => {
  return (dispatch, getState) => {
    const locusList = getState().locusListsByGuid[locusListId]
    if (locusListId && !(locusList && locusList.items)) {
      dispatch({ type: REQUEST_GENE_LIST })
      new HttpRequestHelper(`/api/locus_lists/${locusListId}`,
        (responseJson) => {
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        },
        (e) => {
          const updates = { locusListsByGuid: { [locusListId]: { items: [] } } }
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: updates })
        },
      ).get()
    }
  }
}

export const updateGeneNote = (values) => {
  return updateEntity(values, RECEIVE_DATA, `/api/gene_info/${values.geneId || values.gene_id}/note`, 'noteGuid')
}

export const navigateSavedHashedSearch = (search, navigateSearch) => {
  return (dispatch) => {
    const searchHash = hash.MD5(search)
    dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: { searchesByHash: { [searchHash]: search } } })
    navigateSearch(`/variant_search/results/${searchHash}`)
  }
}

export const loadSavedVariants = (familyGuids, variantGuid, tag) => {
  return (dispatch, getState) => {
    const state = getState()
    const projectGuid = state.currentProjectGuid

    let url = projectGuid ? `/api/project/${projectGuid}/saved_variants` : `/api/staff/saved_variants/${tag}`

    // Do not load if already loaded
    let expectedFamilyGuids
    if (variantGuid) {
      if (state.savedVariantsByGuid[variantGuid]) {
        return
      }
      url = `${url}/${variantGuid}`
    } else if (projectGuid) {
      expectedFamilyGuids = familyGuids
      if (!expectedFamilyGuids) {
        expectedFamilyGuids = Object.values(state.familiesByGuid).filter(
          family => family.projectGuid === projectGuid).map(({ familyGuid }) => familyGuid)
      }
      if (expectedFamilyGuids.length > 0 && expectedFamilyGuids.every(family => state.savedVariantFamilies[family])) {
        return
      }
    } else if (!tag) {
      return
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


const updateSavedVariant = (values, action = 'create') => {
  return (dispatch, getState) => {
    return new HttpRequestHelper(`/api/saved_variant/${action}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post({ searchHash: getState().currentSearchHash, ...values })
  }
}

export const updateVariantNote = (values) => {
  if (values.variantGuid) {
    return updateEntity(values, RECEIVE_DATA, `/api/saved_variant/${values.variantGuid}/note`, 'noteGuid')
  }
  return updateSavedVariant(values)
}

export const updateVariantTags = (values) => {
  const urlPath = values.variantGuid ? `${values.variantGuid}/update_tags` : 'create'
  return updateSavedVariant(values, urlPath)
}

export const updateLocusList = (values) => {
  return (dispatch) => {
    let action = 'create'
    if (values.locusListGuid) {
      action = `${values.locusListGuid}/${values.delete ? 'delete' : 'update'}`
    }

    return new HttpRequestHelper(`/api/locus_lists/${action}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        let error = e.message.replace('(400)', '')
        if (e.body && e.body.invalidLocusListItems) {
          error = `${error} Invalid genes/ intervals: ${e.body.invalidLocusListItems.join(', ')}`
        }
        throw new SubmissionError({
          _error: [error],
        })
      },
    ).post(values)
  }
}

export const updateSavedVariantTable = updates => ({ type: UPDATE_SAVED_VARIANT_TABLE_STATE, updates })
export const updateIgvReadsVisibility = updates => ({ type: UPDATE_IGV_VISIBILITY, updates })


// root reducer
const rootReducer = combineReducers(Object.assign({
  projectCategoriesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectCategoriesByGuid'),
  projectsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectsByGuid'),
  projectsLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_DATA),
  familiesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'familiesByGuid'),
  individualsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'individualsByGuid'),
  samplesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'samplesByGuid'),
  analysisGroupsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'analysisGroupsByGuid'),
  mmeResultsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'mmeResultsByGuid'),
  genesById: createObjectsByIdReducer(RECEIVE_DATA, 'genesById'),
  genesLoading: loadingReducer(REQUEST_GENES, RECEIVE_DATA),
  locusListsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'locusListsByGuid'),
  locusListsLoading: loadingReducer(REQUEST_GENE_LISTS, RECEIVE_DATA),
  locusListLoading: loadingReducer(REQUEST_GENE_LIST, RECEIVE_DATA),
  savedVariantsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'savedVariantsByGuid'),
  savedVariantsLoading: loadingReducer(REQUEST_SAVED_VARIANTS, RECEIVE_DATA),
  searchesByHash: createObjectsByIdReducer(RECEIVE_SAVED_SEARCHES, 'searchesByHash'),
  savedSearchesByGuid: createObjectsByIdReducer(RECEIVE_SAVED_SEARCHES, 'savedSearchesByGuid'),
  savedVariantFamilies: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_FAMILIES),
  savedSearchesLoading: loadingReducer(REQUEST_SAVED_SEARCHES, RECEIVE_SAVED_SEARCHES),
  user: zeroActionsReducer,
  newUser: zeroActionsReducer,
  usersByUsername: createSingleValueReducer(RECEIVE_USERS, {}),
  userOptionsLoading: loadingReducer(REQUEST_USERS, RECEIVE_USERS),
  form: formReducer,
  search: searchReducer,
  savedVariantTableState: createSingleObjectReducer(UPDATE_SAVED_VARIANT_TABLE_STATE, {
    hideExcluded: false,
    hideReviewOnly: false,
    categoryFilter: SHOW_ALL,
    sort: SORT_BY_FAMILY_GUID,
    page: 1,
    recordsPerPage: 25,
  }, false),
  igvReadsVisibility: createSingleObjectReducer(UPDATE_IGV_VISIBILITY),
}, modalReducers, dashboardReducers, projectReducers, searchReducers, staffReducers))

export default rootReducer

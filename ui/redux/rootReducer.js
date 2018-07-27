import { combineReducers } from 'redux'
import { reducer as formReducer, SubmissionError } from 'redux-form'
import { reducer as searchReducer } from 'redux-search'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { reducers as projectReducers } from 'pages/Project/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { createObjectsByIdReducer, loadingReducer, zeroActionsReducer } from './utils/reducerFactories'
import modalReducers from './utils/modalReducer'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
export const RECEIVE_DATA = 'RECEIVE_DATA'
export const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
const RECEIVE_SAVED_VARIANTS = 'RECEIVE_SAVED_VARIANTS'
const REQUEST_VARIANT = 'REQUEST_VARIANT'
const REQUEST_GENES = 'REQUEST_GENES'
const RECEIVE_GENES = 'RECEIVE_GENES'
const REQUEST_GENE_LISTS = 'REQUEST_GENE_LISTS'
const REQUEST_GENE_LIST = 'REQUEST_GENE_LIST'

// action creators

// A helper action that handles create, update and delete requests
const updateEntity = (values, receiveDataAction, urlPath, idField, actionSuffix) => {
  return (dispatch) => {
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
          dispatch({ type: RECEIVE_GENES, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_GENES, error: e.message, updatesById: {} })
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
          dispatch({ type: RECEIVE_GENES, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_GENES, error: e.message, updatesById: {} })
        },
      ).get({ geneIds: [...geneIds] })
    }
  }
}

export const loadLocusLists = (locusListId) => {
  return (dispatch, getState) => {
    const locusList = getState().locusListsByGuid[locusListId]
    if (!locusListId || !locusList || !locusList.items) {
      dispatch({ type: locusListId ? REQUEST_GENE_LIST : REQUEST_GENE_LISTS })
      let url = '/api/locus_lists'
      if (locusListId) {
        url = `${url}/${locusListId}`
      }
      new HttpRequestHelper(url,
        (responseJson) => {
          dispatch({ type: RECEIVE_GENES, updatesById: responseJson.genesById || {} })
          dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        },
        (e) => {
          const updates = locusListId ? { locusListsByGuid: { [locusListId]: { items: [] } } } : {}
          dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: updates })
        },
      ).get()
    }
  }
}

export const loadVariantTranscripts = (variantId) => {
  return (dispatch, getState) => {
    const variant = getState().projectSavedVariants[variantId]
    if (!(variant && variant.transcripts)) {
      dispatch({ type: REQUEST_VARIANT })
      new HttpRequestHelper(`/api/saved_variant/${variantId}/transcripts`,
        (responseJson) => {
          dispatch({ type: RECEIVE_SAVED_VARIANTS, updatesById: responseJson })
        },
        (e) => {
          dispatch({ type: RECEIVE_SAVED_VARIANTS, error: e.message, updatesById: {} })
        },
      ).get()
    }
  }
}

export const updateGeneNote = (values) => {
  return updateEntity(values, RECEIVE_GENES, `/api/gene_info/${values.geneId || values.gene_id}/note`, 'noteGuid')
}

export const updateVariantNote = (values) => {
  return updateEntity(values, RECEIVE_SAVED_VARIANTS, `/api/saved_variant/${values.variantId}/note`, 'noteGuid')
}

export const updateVariantTags = (values) => {
  return (dispatch) => {
    return new HttpRequestHelper(`/api/saved_variant/${values.variantId}/update_tags`,
      (responseJson) => {
        dispatch({ type: RECEIVE_SAVED_VARIANTS, updatesById: responseJson })
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}

export const updateLocusList = (values) => {
  return (dispatch) => {
    let action = 'create'
    if (values.locusListGuid) {
      action = `${values.locusListGuid}/${values.delete ? 'delete' : 'update'}`
    }

    return new HttpRequestHelper(`/api/locus_lists/${action}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_GENES, updatesById: responseJson.genesById || {} })
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        if (responseJson.invalidLocusListItems && responseJson.invalidLocusListItems.length > 0) {
          const err = new Error('This list contains invalid genes/ intervals. All other changes were made successfully.')
          err.body = { ...responseJson, warning: true }
          throw err
        }
      },
      (e) => {
        let errors = [e.message.replace('(400)', '')]
        const invalidItemsError = e.body && e.body.invalidLocusListItems && `Invalid genes/ intervals: ${e.body.invalidLocusListItems.join(', ')}`
        if (invalidItemsError) {
          errors.push(invalidItemsError)
          if (e.body.warning) {
            errors = errors.map(warning => ({ warning }))
          }
        }
        throw new SubmissionError({
          _error: errors,
        })
      },
    ).post(values)
  }
}


// root reducer
const rootReducer = combineReducers(Object.assign({
  projectCategoriesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectCategoriesByGuid'),
  projectsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectsByGuid'),
  projectsLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_DATA),
  familiesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'familiesByGuid'),
  individualsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'individualsByGuid'),
  samplesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'samplesByGuid'),
  matchmakerSubmissions: createObjectsByIdReducer(RECEIVE_DATA, 'matchmakerSubmissions'),
  genesById: createObjectsByIdReducer(RECEIVE_GENES),
  genesLoading: loadingReducer(REQUEST_GENES, RECEIVE_GENES),
  locusListsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'locusListsByGuid'),
  locusListsLoading: loadingReducer(REQUEST_GENE_LISTS, RECEIVE_DATA),
  locusListLoading: loadingReducer(REQUEST_GENE_LIST, RECEIVE_DATA),
  variantLoading: loadingReducer(REQUEST_VARIANT, RECEIVE_SAVED_VARIANTS),
  user: zeroActionsReducer,
  form: formReducer,
  search: searchReducer,
}, modalReducers, dashboardReducers, projectReducers))

export default rootReducer

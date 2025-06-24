import { combineReducers } from 'redux'

import { reducers as dashboardReducers } from 'pages/Dashboard/reducers'
import { reducers as projectReducers } from 'pages/Project/reducers'
import { reducers as searchReducers } from 'pages/Search/reducers'
import { reducers as dataManagementReducers } from 'pages/DataManagement/reducers'
import { reducers as reportReducers } from 'pages/Report/reducers'
import { reducers as summaryDataReducers } from 'pages/SummaryData/reducers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import {
  createObjectsByIdReducer, loadingReducer, zeroActionsReducer, createSingleObjectReducer, createSingleValueReducer,
} from './utils/reducerFactories'
import modalReducers from './utils/modalReducer'
import {
  RECEIVE_DATA,
  REQUEST_PROJECTS,
  RECEIVE_PROJECT_CHILD_ENTITES,
  RECEIVE_SAVED_SEARCHES,
  REQUEST_SAVED_VARIANTS,
  REQUEST_PROJECT_DETAILS,
  REQUEST_ANALYSIS_GROUPS,
  RECEIVE_ANALYSIS_GROUPS,
  updateEntity,
  loadFamilyData,
} from './utils/reducerUtils'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const REQUEST_GENES = 'REQUEST_GENES'
const REQUEST_GENE_LISTS = 'REQUEST_GENE_LISTS'
const RECEIVE_GENE_LISTS = 'RECEIVE_GENE_LISTS'
const REQUEST_GENE_LIST = 'REQUEST_GENE_LIST'
const REQUEST_USER_OPTIONS = 'REQUEST_USER_OPTIONS'
const RECEIVE_USER_OPTIONS = 'RECEIVE_USER_OPTIONS'
const UPDATE_USER = 'UPDATE_USER'
const REQUEST_HPO_TERMS = 'REQUEST_HPO_TERMS'
const RECEIVE_HPO_TERMS = 'RECEIVE_HPO_TERMS'
const REQUEST_FAMILY_DETAILS = 'REQUEST_FAMILY_DETAILS'

// action creators

export const fetchProjects = () => (dispatch) => {
  dispatch({ type: REQUEST_PROJECTS })
  new HttpRequestHelper('/api/dashboard',
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
    },
    e => dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })).get()
}

export const loadUserOptions = familyGuid => (dispatch, getState) => {
  let url = '/api/users/get_options'
  if (familyGuid) {
    const { projectGuid } = getState().familiesByGuid[familyGuid]
    url = `${url}/${projectGuid}`
  }
  dispatch({ type: REQUEST_USER_OPTIONS })
  new HttpRequestHelper(url,
    (responseJson) => {
      dispatch({ type: RECEIVE_USER_OPTIONS, newValue: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_USER_OPTIONS, error: e.message, newValue: [] })
    }).get()
}

export const updateUser = values => dispatch => new HttpRequestHelper('/api/users/update',
  (responseJson) => {
    dispatch({ type: UPDATE_USER, updates: responseJson })
  }).post(values)

export const updateProject = (values) => {
  const actionSuffix = values.projectField ? `_project_${values.projectField}` : '_project'
  return updateEntity(values, RECEIVE_DATA, '/api/project', 'projectGuid', actionSuffix)
}

export const loadFamilyDetails = familyGuid => loadFamilyData(
  familyGuid, 'detailsLoaded', 'details', REQUEST_FAMILY_DETAILS, true,
)

export const updateFamily = (values) => {
  if (values.delete) {
    return dispatch => new HttpRequestHelper(`/api/project/${values.projectGuid}/delete_families`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      }).post({ families: [values] })
  }

  const urlBase = `/api/family/${values.familyGuid}`
  if (values.nestedField) {
    return updateEntity(values, RECEIVE_DATA, `${urlBase}/${values.nestedField}`, `${values.nestedField}Guid`)
  }

  const familyField = values.familyField ? `_${values.familyField}` : ''
  return dispatch => new HttpRequestHelper(`${urlBase}/update${familyField}`,
    (responseJson) => {
      const updatesById = values.rawResponse ? responseJson : { familiesByGuid: responseJson }
      dispatch({ type: RECEIVE_DATA, updatesById })
    }).post(values)
}

export const updateIndividual = values => (dispatch) => {
  const individualField = values.individualField ? `_${values.individualField}` : ''
  return new HttpRequestHelper(`/api/individual/${values.individualGuid}/update${individualField}`,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: { individualsByGuid: responseJson } })
    }).post(values)
}

export const loadGene = geneId => (dispatch, getState) => {
  const gene = getState().genesById[geneId]
  if (!gene || !gene.notes) {
    dispatch({ type: REQUEST_GENES })
    new HttpRequestHelper(`/api/gene_info/${geneId}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).get()
  }
}

export const loadGenes = geneIds => (dispatch, getState) => {
  const state = getState()
  if ([...geneIds].some(geneId => !state.genesById[geneId])) {
    dispatch({ type: REQUEST_GENES })
    new HttpRequestHelper('/api/genes_info',
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).get({ geneIds: [...geneIds] })
  }
}

export const loadLocusLists = allProjectLists => (dispatch) => {
  dispatch({ type: REQUEST_GENE_LISTS })
  new HttpRequestHelper(`/api/${allProjectLists ? 'all_locus_list_options' : 'locus_lists'}`,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      dispatch({ type: RECEIVE_GENE_LISTS, updatesById: {} })
    },
    (e) => {
      dispatch({ type: RECEIVE_GENE_LISTS, error: e.message, updatesById: {} })
    }).get()
}

export const loadLocusListItems = locusListId => (dispatch, getState) => {
  if (!locusListId) {
    return
  }
  const locusList = getState().locusListsByGuid[locusListId]
  const isLoaded = locusList && locusList.items &&
    (!locusList.paLocusList || locusList.items.some(({ pagene }) => pagene))
  if (!isLoaded) {
    dispatch({ type: REQUEST_GENE_LIST })
    new HttpRequestHelper(`/api/locus_lists/${locusListId}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        const updates = { locusListsByGuid: { [locusListId]: { items: [] } } }
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: updates })
      }).get()
  }
}

export const loadHpoTerms = hpoId => (dispatch, getState) => {
  if (!getState().hpoTermsByParent[hpoId]) {
    dispatch({ type: REQUEST_HPO_TERMS })
    new HttpRequestHelper(`/api/hpo_terms/${hpoId}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_HPO_TERMS, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_HPO_TERMS, error: e.message, updatesById: {} })
      }).get()
  }
}

export const updateGeneNote = values => updateEntity(
  values, RECEIVE_DATA, `/api/gene_info/${values.geneId || values.gene_id}/note`, 'noteGuid',
)

const navigateSavedHashedSearchHelper = (resultsPath, hashKey) => (search, navigateSearch) => (dispatch) => {
  // lazy load object-hash library as it is not used anywhere else
  import('object-hash').then((hash) => {
    const searchHash = hash.default.MD5(search)
    dispatch({ type: RECEIVE_SAVED_SEARCHES, updatesById: { [hashKey]: { [searchHash]: search } } })
    const resultsLink = `/variant_search/${resultsPath}/${searchHash}`
    if (navigateSearch) {
      navigateSearch(resultsLink)
    } else {
      window.open(resultsLink, '_blank')
    }
  })
}

export const navigateSavedHashedSearch = navigateSavedHashedSearchHelper('results', 'searchesByHash')
export const navigateFamiliesSearch = navigateSavedHashedSearchHelper('families', 'searchFamiliesByHash')

const updateSavedVariant = (values, action = 'create') => (dispatch, getState) => new HttpRequestHelper(
  `/api/saved_variant/${action}`,
  (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
  },
).post({ searchHash: getState().currentSearchHash, ...values })

export const updateVariantNote = (values) => {
  if (values.variantGuids) {
    return updateEntity(values, RECEIVE_DATA, `/api/saved_variant/${values.variantGuids}/note`, 'noteGuid')
  }
  return updateSavedVariant(values)
}

export const updateVariantTags = (values, tagType = 'tags') => {
  const urlPath = values.variantGuids ? `${values.variantGuids}/update_${tagType}` : 'create'
  return updateSavedVariant(values, urlPath)
}

export const updateVariantClassification = values => updateSavedVariant(values, `${values.variant.variantGuid}/update_acmg_classification`)

export const updateVariantMainTranscript = (variantGuid, transcriptId) => dispatch => new HttpRequestHelper(
  `/api/saved_variant/${variantGuid}/update_transcript/${transcriptId}`,
  (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
  },
).post()

export const updateLocusList = values => (dispatch) => {
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
      throw new Error(error)
    }).post(values)
}

// root reducer
const rootReducer = combineReducers({
  projectCategoriesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectCategoriesByGuid'),
  projectsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'projectsByGuid'),
  projectsLoading: loadingReducer(REQUEST_PROJECTS, RECEIVE_DATA),
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_DATA),
  loadedProjectChildEntities: createObjectsByIdReducer(RECEIVE_PROJECT_CHILD_ENTITES),
  familiesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'familiesByGuid'),
  familyNotesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'familyNotesByGuid'),
  familyDetailsLoading: createSingleObjectReducer(REQUEST_FAMILY_DETAILS),
  individualsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'individualsByGuid'),
  samplesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'samplesByGuid'),
  igvSamplesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'igvSamplesByGuid'),
  analysisGroupsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'analysisGroupsByGuid'),
  analysisGroupsLoading: loadingReducer(REQUEST_ANALYSIS_GROUPS, RECEIVE_ANALYSIS_GROUPS),
  mmeSubmissionsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'mmeSubmissionsByGuid'),
  mmeResultsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'mmeResultsByGuid'),
  genesById: createObjectsByIdReducer(RECEIVE_DATA, 'genesById'),
  omimIntervals: createObjectsByIdReducer(RECEIVE_DATA, 'omimIntervals'),
  rnaSeqDataByIndividual: createObjectsByIdReducer(RECEIVE_DATA, 'rnaSeqData'),
  phenotypeGeneScoresByIndividual: createObjectsByIdReducer(RECEIVE_DATA, 'phenotypeGeneScores'),
  genesLoading: loadingReducer(REQUEST_GENES, RECEIVE_DATA),
  hpoTermsByParent: createObjectsByIdReducer(RECEIVE_HPO_TERMS),
  hpoTermsLoading: loadingReducer(REQUEST_HPO_TERMS, RECEIVE_HPO_TERMS),
  locusListsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'locusListsByGuid'),
  locusListsLoading: loadingReducer(REQUEST_GENE_LISTS, RECEIVE_GENE_LISTS),
  locusListLoading: loadingReducer(REQUEST_GENE_LIST, RECEIVE_DATA),
  savedVariantsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'savedVariantsByGuid'),
  savedVariantsLoading: loadingReducer(REQUEST_SAVED_VARIANTS, RECEIVE_DATA),
  variantTagsByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'variantTagsByGuid'),
  variantNotesByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'variantNotesByGuid'),
  variantFunctionalDataByGuid: createObjectsByIdReducer(RECEIVE_DATA, 'variantFunctionalDataByGuid'),
  searchesByHash: createObjectsByIdReducer(RECEIVE_SAVED_SEARCHES, 'searchesByHash'),
  searchFamiliesByHash: createObjectsByIdReducer(RECEIVE_SAVED_SEARCHES, 'searchFamiliesByHash'),
  transcriptsById: createObjectsByIdReducer(RECEIVE_DATA, 'transcriptsById'),
  totalSampleCounts: createObjectsByIdReducer(RECEIVE_DATA, 'totalSampleCounts'),
  user: createSingleObjectReducer(UPDATE_USER),
  newUser: zeroActionsReducer,
  userOptionsByUsername: createSingleValueReducer(RECEIVE_USER_OPTIONS, {}),
  userOptionsLoading: loadingReducer(REQUEST_USER_OPTIONS, RECEIVE_USER_OPTIONS),
  meta: zeroActionsReducer,
  ...modalReducers,
  ...dashboardReducers,
  ...projectReducers,
  ...searchReducers,
  ...reportReducers,
  ...dataManagementReducers,
  ...summaryDataReducers,
})

export default rootReducer

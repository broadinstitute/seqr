import { combineReducers } from 'redux'

import {
  loadingReducer, createSingleObjectReducer, createSingleValueReducer, createObjectsByIdReducer,
} from 'redux/utils/reducerFactories'
import { REQUEST_SAVED_VARIANTS, updateEntity, loadProjectChildEntities, loadFamilyData } from 'redux/utils/reducerUtils'
import { SHOW_ALL, SORT_BY_FAMILY_GUID, NOTE_TAG_NAME } from 'shared/utils/constants'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { SHOW_IN_REVIEW, SORT_BY_FAMILY_NAME, SORT_BY_FAMILY_ADDED_DATE, CASE_REVIEW_TABLE_NAME } from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const RECEIVE_DATA = 'RECEIVE_DATA'
const UPDATE_FAMILY_TABLE_STATE = 'UPDATE_FAMILY_TABLE_STATE'
const UPDATE_FAMILY_TABLE_FILTER_STATE = 'UPDATE_FAMILY_TABLE_FILTER_STATE'
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'
const UPDATE_CURRENT_PROJECT = 'UPDATE_CURRENT_PROJECT'
const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
const RECEIVE_SAVED_VARIANT_FAMILIES = 'RECEIVE_SAVED_VARIANT_FAMILIES'
const UPDATE_SAVED_VARIANT_TABLE_STATE = 'UPDATE_VARIANT_STATE'
const REQUEST_MME_MATCHES = 'REQUEST_MME_MATCHES'
const REQUEST_RNA_SEQ_DATA = 'REQUEST_RNA_SEQ_DATA'
const REQUEST_PROJECT_OVERVIEW = 'REQUEST_PROJECT_OVERVIEW'
const REQUEST_FAMILIES = 'REQUEST_FAMILIES'
const RECEIVE_FAMILIES = 'RECEIVE_FAMILIES'
const REQUEST_FAMILY_VARIANT_SUMMARY = 'REQUEST_FAMILY_VARIANT_SUMMARY'
const REQUEST_INDIVIDUALS = 'REQUEST_INDIVIDUALS'
const REQUEST_MME_SUBMISSIONS = 'REQUEST_MME_SUBMISSIONS'

// Data actions

export const loadCurrentProject = projectGuid => (dispatch, getState) => {
  dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: projectGuid })
  const project = getState().projectsByGuid[projectGuid]
  if (!project) {
    dispatch({ type: REQUEST_PROJECT_DETAILS })
    new HttpRequestHelper(`/api/project/${projectGuid}/details`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).get()
  }
}

const loadCurrentProjectChildEntities = (entityType, dispatchType, receiveDispatchType) => (dispatch, getState) => {
  const { currentProjectGuid } = getState()
  return loadProjectChildEntities(currentProjectGuid, entityType, dispatchType, receiveDispatchType)(dispatch, getState)
}

export const loadFamilies = () => loadCurrentProjectChildEntities('families', REQUEST_FAMILIES, RECEIVE_FAMILIES)

export const loadIndividuals = () => loadCurrentProjectChildEntities('individuals', REQUEST_INDIVIDUALS)

export const loadMmeSubmissions = () => loadCurrentProjectChildEntities('mme submissions', REQUEST_MME_SUBMISSIONS)

const loadFamilyNotes = () => loadCurrentProjectChildEntities('family notes', REQUEST_FAMILIES, RECEIVE_FAMILIES)

export const loadProjectExportData = () => (dispatch, getState) => Promise.all([
  loadIndividuals()(dispatch, getState),
  loadFamilyNotes()(dispatch, getState),
])

export const loadProjectOverview = () => (dispatch, getState) => {
  const { currentProjectGuid, projectsByGuid } = getState()
  const project = projectsByGuid[currentProjectGuid]
  if (!project.detailsLoaded) {
    dispatch({ type: REQUEST_PROJECT_OVERVIEW })
    new HttpRequestHelper(`/api/project/${currentProjectGuid}/get_overview`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).get()
  }
}

export const loadFamilyVariantSummary = familyGuid => loadFamilyData(
  familyGuid, 'discoveryTags', 'variant_tag_summary', REQUEST_FAMILY_VARIANT_SUMMARY,
)

export const loadSavedVariants = ({ familyGuids, variantGuid, tag }) => (dispatch, getState) => {
  const state = getState()
  const projectGuid = state.currentProjectGuid

  let url = `/api/project/${projectGuid}/saved_variants`

  const loadNotes = tag === NOTE_TAG_NAME || familyGuids

  // Do not load if already loaded
  let expectedFamilyGuids
  if (variantGuid) {
    if (state.savedVariantsByGuid[variantGuid]) {
      return
    }
    url = `${url}/${variantGuid}`
  } else {
    expectedFamilyGuids = familyGuids
    if (!expectedFamilyGuids && state.projectsByGuid[projectGuid].familiesLoaded) {
      expectedFamilyGuids = Object.values(state.familiesByGuid).filter(
        family => family.projectGuid === projectGuid,
      ).map(({ familyGuid }) => familyGuid)
    }

    if ((expectedFamilyGuids || []).length > 0 && expectedFamilyGuids.every((family) => {
      const { loaded, noteVariants } = state.savedVariantFamilies[family] || {}
      return loaded && (noteVariants || !loadNotes)
    })) {
      return
    }
  }

  const params = {
    loadFamilyContext: !(expectedFamilyGuids || []).length || expectedFamilyGuids.some(
      familyGuid => !state.familiesByGuid[familyGuid]?.detailsLoaded,
    ),
    loadProjectTagTypes: !state.projectsByGuid[projectGuid].variantTagTypes,
    includeLocusLists: !state.projectsByGuid[projectGuid].locusListGuids,
  }
  if (familyGuids) {
    params.families = familyGuids.join(',')
  } else if (loadNotes) {
    params.includeNoteVariants = true
  }

  dispatch({ type: REQUEST_SAVED_VARIANTS })
  new HttpRequestHelper(url,
    (responseJson) => {
      if (expectedFamilyGuids || responseJson.familiesByGuid) {
        dispatch({
          type: RECEIVE_SAVED_VARIANT_FAMILIES,
          updates: (expectedFamilyGuids || Object.keys(responseJson.familiesByGuid)).reduce(
            (acc, family) => ({ ...acc, [family]: { loaded: true, noteVariants: loadNotes } }), {},
          ),
        })
      }
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
    }).get(params)
}

export const loadFamilySavedVariants = familyGuid => loadSavedVariants({ familyGuids: [familyGuid] })

const unloadSavedVariants = (dispatch, getState) => {
  const state = getState()
  const variantsToDelete = Object.keys(state.savedVariantsByGuid).reduce((acc, o) => ({ ...acc, [o]: null }), {})
  const variantFamiliesToDelete = Object.keys(state.savedVariantFamilies).reduce((acc, o) => (
    { ...acc, [o]: { loaded: false } }), {})
  dispatch({ type: RECEIVE_DATA, updatesById: { savedVariantsByGuid: variantsToDelete } })
  dispatch({ type: RECEIVE_SAVED_VARIANT_FAMILIES, updates: variantFamiliesToDelete })
}

export const unloadProject = () => dispatch => dispatch({ type: UPDATE_CURRENT_PROJECT, newValue: null })

export const updateFamilies = values => (dispatch, getState) => {
  const action = values.delete ? 'delete' : 'edit'
  return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/${action}_families`,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
    }).post(values)
}

export const updateIndividuals = values => (dispatch, getState) => {
  let action = 'edit_individuals'
  if (values.uploadedFileId) {
    action = `save_individuals_table/${values.uploadedFileId}`
  } else if (values.delete) {
    action = 'delete_individuals'
  }

  return new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/${action}`,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
    }).post(values)
}

export const updateIndividualsMetadata = ({ uploadedFileId }) => (dispatch, getState) => new HttpRequestHelper(
  `/api/project/${getState().currentProjectGuid}/save_individuals_metadata_table/${uploadedFileId}`,
  (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
  },
).post()

export const addVariantsDataset = values => (dispatch, getState) => new HttpRequestHelper(
  `/api/project/${getState().currentProjectGuid}/add_dataset/variants`,
  (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: responseJson })

    // Clear all loaded variants and update the saved variant json. This should happen asynchronously
    unloadSavedVariants(dispatch, getState)
    new HttpRequestHelper(`/api/project/${getState().currentProjectGuid}/update_saved_variant_json`, () => {}).post()
  },
).post(values)

export const addIGVDataset = ({ mappingFile, ...values }) => (dispatch, getState) => {
  const errors = []

  return Promise.all(mappingFile.updates.map(
    ({ individualGuid, ...update }) => new HttpRequestHelper(
      `/api/individual/${individualGuid}/update_igv_sample`,
      responseJson => dispatch({ type: RECEIVE_DATA, updatesById: responseJson }),
      e => errors.push(`Error updating ${getState().individualsByGuid[individualGuid].individualId}: ${e.body && e.body.error ? e.body.error : e.message}`),
    ).post({ ...update, ...values }),
  )).then(() => {
    if (errors.length) {
      const err = new Error()
      err.body = { errors }
      throw err
    }
  })
}

export const updateLocusLists = values => (dispatch, getState) => {
  const projectGuid = getState().currentProjectGuid
  const action = values.delete ? 'delete' : 'add'
  return new HttpRequestHelper(`/api/project/${projectGuid}/${action}_locus_lists`,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: { projectsByGuid: { [projectGuid]: responseJson } } })
    }).post(values)
}

export const updateAnvilWorkspace = values => (dispatch, getState) => {
  const projectGuid = getState().currentProjectGuid
  return new HttpRequestHelper(`/api/project/${projectGuid}/update_workspace`,
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: { projectsByGuid: { [projectGuid]: responseJson } } })
    }).post(values)
}

export const updateCollaborator = values => updateEntity(
  values, RECEIVE_DATA, null, 'username', null, state => `/api/project/${state.currentProjectGuid}/collaborators`,
)

export const updateAnalysisGroup = values => updateEntity(
  values, RECEIVE_DATA, null, 'analysisGroupGuid', null, state => `/api/project/${state.currentProjectGuid}/analysis_groups`,
)

export const loadMmeMatches = (submissionGuid, search) => (dispatch, getState) => {
  const state = getState()
  const submission = state.mmeSubmissionsByGuid[submissionGuid]
  if (submission && (!submission.mmeResultGuids || search)) {
    const { familyGuid } = state.individualsByGuid[submission.individualGuid]
    dispatch({ type: REQUEST_MME_MATCHES })
    new HttpRequestHelper(`/api/matchmaker/${search ? 'search' : 'get'}_mme_matches/${submissionGuid}`,
      (responseJson) => {
        dispatch({
          type: RECEIVE_SAVED_VARIANT_FAMILIES, updates: { [familyGuid]: { loaded: true, noteVariants: true } },
        })
        dispatch({
          type: RECEIVE_DATA,
          updatesById: responseJson,
        })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).get()
  }
}

export const loadRnaSeqData = individualGuid => (dispatch, getState) => {
  const data = getState().rnaSeqDataByIndividual[individualGuid]
  // If variants were loaded for the individual, the significant gene data will be loaded but not all the needed data
  if (!data?.outliers || Object.values(data.outliers).every(({ isSignificant }) => isSignificant)) {
    dispatch({ type: REQUEST_RNA_SEQ_DATA })
    new HttpRequestHelper(`/api/individual/${individualGuid}/rna_seq_data`,
      (responseJson) => {
        dispatch({
          type: RECEIVE_DATA, updatesById: responseJson,
        })
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
      }).get()
  }
}

export const updateMmeSubmission = (values) => {
  const onSuccess = values.delete ? null : (responseJson, dispatch, getState) => (
    loadMmeMatches(Object.keys(responseJson.mmeSubmissionsByGuid)[0], true)(dispatch, getState)
  )
  return updateEntity(values, RECEIVE_DATA, '/api/matchmaker/submission', 'submissionGuid', null, null, onSuccess)
}

export const updateMmeSubmissionStatus = values => updateEntity(
  values, RECEIVE_DATA, '/api/matchmaker/result_status', 'matchmakerResultGuid',
)

export const updateMmeContactNotes = values => updateEntity(
  values, RECEIVE_DATA, '/api/matchmaker/contact_notes', 'institution',
)

export const sendMmeContactEmail = values => dispatch => new HttpRequestHelper(
  `/api/matchmaker/send_email/${values.matchmakerResultGuid}`,
  (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
  },
).post(values)

export const updateProjectMmeContact = values => (dispatch, getState) => new HttpRequestHelper(
  `/api/matchmaker/update_project_contact/${getState().currentProjectGuid}`,
  (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
  },
).post(values)

// Table actions
export const updateFamiliesTable = (updates, tableName) => (
  { type: tableName === CASE_REVIEW_TABLE_NAME ? UPDATE_CASE_REVIEW_TABLE_STATE : UPDATE_FAMILY_TABLE_STATE, updates }
)

export const updateFamiliesTableFilters = updates => ({ type: UPDATE_FAMILY_TABLE_FILTER_STATE, updates })

export const updateSavedVariantTable = updates => ({ type: UPDATE_SAVED_VARIANT_TABLE_STATE, updates })

// reducers

export const reducers = {
  currentProjectGuid: createSingleValueReducer(UPDATE_CURRENT_PROJECT, null),
  projectDetailsLoading: loadingReducer(REQUEST_PROJECT_DETAILS, RECEIVE_DATA),
  matchmakerMatchesLoading: loadingReducer(REQUEST_MME_MATCHES, RECEIVE_DATA),
  mmeContactNotes: createObjectsByIdReducer(RECEIVE_DATA, 'mmeContactNotes'),
  rnaSeqDataLoading: loadingReducer(REQUEST_RNA_SEQ_DATA, RECEIVE_DATA),
  familyTagTypeCounts: createObjectsByIdReducer(RECEIVE_DATA, 'familyTagTypeCounts'),
  savedVariantFamilies: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_FAMILIES),
  familiesLoading: loadingReducer(REQUEST_FAMILIES, RECEIVE_FAMILIES),
  familyVariantSummaryLoading: loadingReducer(REQUEST_FAMILY_VARIANT_SUMMARY, RECEIVE_DATA),
  individualsLoading: loadingReducer(REQUEST_INDIVIDUALS, RECEIVE_DATA),
  mmeSubmissionsLoading: loadingReducer(REQUEST_MME_SUBMISSIONS, RECEIVE_DATA),
  projectOverviewLoading: loadingReducer(REQUEST_PROJECT_OVERVIEW, RECEIVE_DATA),
  familyTableState: createSingleObjectReducer(UPDATE_FAMILY_TABLE_STATE, {
    familiesSearch: '',
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
  }, false),
  familyTableFilterState: createSingleObjectReducer(UPDATE_FAMILY_TABLE_FILTER_STATE),
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

import { combineReducers } from 'redux'

import { loadingReducer, createSingleValueReducer, createSingleObjectReducer } from 'redux/utils/reducerFactories'
import { RECEIVE_DATA, REQUEST_SAVED_VARIANTS } from 'redux/utils/reducerUtils'
import { SHOW_ALL, SORT_BY_XPOS } from 'shared/utils/constants'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_SUCCESS_STORY = 'REQUEST_SUCCESS_STORY'
const RECEIVE_SUCCESS_STORY = 'RECEIVE_SUCCESS_STORY'
const REQUEST_MME = 'REQUEST_MME'
const RECEIVE_MME = 'RECEIVE_MME'
const RECEIVE_SAVED_VARIANT_TAGS = 'RECEIVE_SAVED_VARIANT_TAGS'
const UPDATE_ALL_PROJECT_SAVED_VARIANT_TABLE_STATE = 'UPDATE_ALL_PROJECT_VARIANT_STATE'
const RECEIVE_EXTERNAL_ANALYSIS_UPLOAD_STATS = 'RECEIVE_EXTERNAL_ANALYSIS_UPLOAD_STATS'

// Data actions

export const loadMme = () => (dispatch) => {
  dispatch({ type: REQUEST_MME })
  new HttpRequestHelper('/api/summary_data/matchmaker',
    (responseJson) => {
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      dispatch({ type: RECEIVE_MME, newValue: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_MME, error: e.message, newValue: [] })
    }).get()
}

export const loadSuccessStory = successStoryTypes => (dispatch) => {
  if (successStoryTypes) {
    dispatch({ type: REQUEST_SUCCESS_STORY })
    new HttpRequestHelper(`/api/summary_data/success_story/${successStoryTypes}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_SUCCESS_STORY, newValue: responseJson.rows })
      },
      (e) => {
        dispatch({ type: RECEIVE_SUCCESS_STORY, error: e.message, newValue: [] })
      }).get()
  }
}

export const loadSavedVariants = ({ tag, gene = '' }) => (dispatch, getState) => {
  // Do not load if already loaded
  if (tag && tag !== SHOW_ALL) {
    const loadedTags = getState().savedVariantTags
    if (loadedTags[tag] || tag.split(';').some(t => loadedTags[t])) {
      return
    }
  } else if (!gene) {
    return
  }

  dispatch({ type: REQUEST_SAVED_VARIANTS })
  new HttpRequestHelper(`/api/summary_data/saved_variants/${tag}`,
    (responseJson) => {
      if (tag && !gene) {
        dispatch({
          type: RECEIVE_SAVED_VARIANT_TAGS,
          updates: { [tag]: true },
        })
      }
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
    }).get({ gene })
}

export const updateAllProjectSavedVariantTable = updates => (
  { type: UPDATE_ALL_PROJECT_SAVED_VARIANT_TABLE_STATE, updates })

export const updateExternalAnalysis = values => dispatch => new HttpRequestHelper(
  '/api/summary_data/update_external_analysis',
  (responseJson) => {
    dispatch({ type: RECEIVE_EXTERNAL_ANALYSIS_UPLOAD_STATS, newValue: responseJson })
  },
).post(values)

export const sendVlmContactEmail = values => () => new HttpRequestHelper(
  '/api/summary_data/send_vlm_email',
).post(values)

export const reducers = {
  successStoryLoading: loadingReducer(REQUEST_SUCCESS_STORY, RECEIVE_SUCCESS_STORY),
  successStoryRows: createSingleValueReducer(RECEIVE_SUCCESS_STORY, []),
  mmeLoading: loadingReducer(REQUEST_MME, RECEIVE_MME),
  mmeMetrics: createSingleValueReducer(RECEIVE_MME, {}, 'metrics'),
  mmeSubmissions: createSingleValueReducer(RECEIVE_MME, [], 'submissions'),
  savedVariantTags: createSingleObjectReducer(RECEIVE_SAVED_VARIANT_TAGS),
  externalAnalysisUploadStats: createSingleValueReducer(RECEIVE_EXTERNAL_ANALYSIS_UPLOAD_STATS, {}),
  allProjectSavedVariantTableState: createSingleObjectReducer(UPDATE_ALL_PROJECT_SAVED_VARIANT_TABLE_STATE, {
    sort: SORT_BY_XPOS,
    page: 1,
    recordsPerPage: 25,
  }, false),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

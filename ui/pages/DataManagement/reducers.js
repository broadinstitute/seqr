import { combineReducers } from 'redux'

import { loadingReducer, createSingleValueReducer, createSingleObjectReducer } from 'redux/utils/reducerFactories'
import { HttpRequestHelper, loadMultipleData } from 'shared/utils/httpRequestHelper'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
const REQUEST_ELASTICSEARCH_STATUS = 'REQUEST_ELASTICSEARCH_STATUS'
const RECEIVE_ELASTICSEARCH_STATUS = 'RECEIVE_ELASTICSEARCH_STATUS'
const RECEIVE_RNA_SEQ_UPLOAD_STATS = 'RECEIVE_RNA_SEQ_UPLOAD_STATS'
const RECEIVE_PHE_PRI_UPLOAD_STATS = 'RECEIVE_PHE_PRI_UPLOAD_STATS'
const RECEIVE_IGV_UPLOAD_STATS = 'RECEIVE_IGV_UPLOAD_STATS'
const REQUEST_ALL_USERS = 'REQUEST_ALL_USERS'
const RECEIVE_ALL_USERS = 'RECEIVE_ALL_USERS'

// Data actions
export const loadElasticsearchStatus = () => (dispatch) => {
  dispatch({ type: REQUEST_ELASTICSEARCH_STATUS })
  new HttpRequestHelper('/api/data_management/elasticsearch_status',
    (responseJson) => {
      dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, updates: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_ELASTICSEARCH_STATUS, error: e.message, updates: { errors: [e.message] } })
    }).get()
}

export const loadAllUsers = () => (dispatch, getState) => {
  const { allUsers } = getState()
  if (allUsers && allUsers.length) {
    return
  }

  dispatch({ type: REQUEST_ALL_USERS })
  new HttpRequestHelper('/api/data_management/get_all_users',
    (responseJson) => {
      dispatch({ type: RECEIVE_ALL_USERS, newValue: responseJson })
    },
    (e) => {
      dispatch({ type: RECEIVE_ALL_USERS, error: e.message, newValue: [] })
    }).get()
}

const submitRequest = (urlPath, receiveDataAction, values) => dispatch => new HttpRequestHelper(
  `/api/data_management/${urlPath}`,
  (responseJson) => {
    dispatch({ type: receiveDataAction, newValue: responseJson })
  },
).post(values)

export const deleteEsIndex = index => submitRequest('delete_index', RECEIVE_ELASTICSEARCH_STATUS, { index })

export const uploadRnaSeq = loadMultipleData(
  '/api/data_management/update_rna_seq',
  ({ sampleGuids, fileName }, { dataType }) => sampleGuids.map(sampleGuid => ([
    `/api/load_rna_seq_sample/${sampleGuid}`, sampleGuid, { fileName, dataType },
  ])),
  RECEIVE_RNA_SEQ_UPLOAD_STATS,
  numLoaded => `Successfully loaded data for ${numLoaded} RNA-seq samples`,
  10,
)

export const addIgv = loadMultipleData(
  '/api/data_management/add_igv',
  ({ updates }) => updates.map(({ individualGuid, individualId, ...update }) => ([
    `/api/individual/${individualGuid}/update_igv_sample`, individualId, update,
  ])),
  RECEIVE_IGV_UPLOAD_STATS,
  numLoaded => `Successfully added IGV tracks for ${numLoaded} samples`,
)

export const uploadPhenotypePrioritization = values => submitRequest(
  'load_phenotype_prioritization_data', RECEIVE_PHE_PRI_UPLOAD_STATS, values,
)

export const reducers = {
  elasticsearchStatusLoading: loadingReducer(REQUEST_ELASTICSEARCH_STATUS, RECEIVE_ELASTICSEARCH_STATUS),
  elasticsearchStatus: createSingleObjectReducer(RECEIVE_ELASTICSEARCH_STATUS),
  rnaSeqUploadStats: createSingleValueReducer(RECEIVE_RNA_SEQ_UPLOAD_STATS, {}),
  phePriUploadStats: createSingleValueReducer(RECEIVE_PHE_PRI_UPLOAD_STATS, {}),
  igvUploadStats: createSingleValueReducer(RECEIVE_IGV_UPLOAD_STATS, {}),
  allUsers: createSingleValueReducer(RECEIVE_ALL_USERS, [], 'users'),
  allUsersLoading: loadingReducer(REQUEST_ALL_USERS, RECEIVE_ALL_USERS),
}

const rootReducer = combineReducers(reducers)

export default rootReducer

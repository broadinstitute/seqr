import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { toCamelcase, toSnakecase } from 'shared/utils/stringUtils'

// actions
export const RECEIVE_DATA = 'RECEIVE_DATA'
export const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
export const RECEIVE_SAVED_SEARCHES = 'RECEIVE_SAVED_SEARCHES'
export const REQUEST_SAVED_SEARCHES = 'REQUEST_SAVED_SEARCHES'
export const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
export const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
export const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'

// A helper action that handles create, update and delete requests
export const updateEntity = (
  values, receiveDataAction, urlPath, idField, actionSuffix, getUrlPath, onSuccess,
) => (dispatch, getState) => {
  let action = 'create'
  let subPath = ''
  if (values[idField]) {
    subPath = `/${values[idField]}`
    action = values.delete ? 'delete' : 'update'
  }

  const url = `${getUrlPath ? getUrlPath(getState()) : urlPath}${subPath}/${action}${actionSuffix || ''}`
  return new HttpRequestHelper(url,
    (responseJson) => {
      dispatch({ type: receiveDataAction, updatesById: responseJson })
      if (onSuccess) {
        onSuccess(responseJson, dispatch, getState)
      }
    }).post(values)
}

export const loadProjectChildEntities = (
  projectGuid, entityType, dispatchType, receiveDispatchType,
) => (dispatch, getState) => {
  const { projectsByGuid } = getState()
  const project = projectsByGuid[projectGuid]

  if (!project[`${toCamelcase(entityType)}Loaded`]) {
    dispatch({ type: dispatchType })
    new HttpRequestHelper(`/api/project/${projectGuid}/get_${toSnakecase(entityType)}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        if (receiveDispatchType) {
          dispatch({ type: receiveDispatchType, updatesById: responseJson })
        }
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        if (receiveDispatchType) {
          dispatch({ type: receiveDispatchType, updatesById: {} })
        }
      }).get()
  }
}

export const loadFamilyData = (familyGuid, detailField, urlPath, dispatchType, dispatchOnReceive) => (
  dispatch, getState,
) => {
  const { familiesByGuid } = getState()
  const family = familiesByGuid[familyGuid]
  if (!family || !family[detailField]) {
    dispatch({ type: dispatchType, updates: { [familyGuid]: true } })
    new HttpRequestHelper(`/api/family/${familyGuid}/${urlPath}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        if (dispatchOnReceive) {
          dispatch({ type: dispatchType, updates: { [familyGuid]: false } })
        }
      },
      (e) => {
        dispatch({ type: RECEIVE_DATA, error: e.message, updatesById: {} })
        if (dispatchOnReceive) {
          dispatch({ type: dispatchType, updates: { [familyGuid]: false } })
        }
      }).get()
  }
}

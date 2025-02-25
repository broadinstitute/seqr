import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { toSnakecase } from 'shared/utils/stringUtils'

// actions
export const RECEIVE_DATA = 'RECEIVE_DATA'
export const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
export const REQUEST_PROJECT_DETAILS = 'REQUEST_PROJECT_DETAILS'
export const RECEIVE_PROJECT_CHILD_ENTITES = 'RECEIVE_PROJECT_CHILD_ENTITES'
export const RECEIVE_SAVED_SEARCHES = 'RECEIVE_SAVED_SEARCHES'
export const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
export const REQUEST_ANALYSIS_GROUPS = 'REQUEST_ANALYSIS_GROUPS'
export const RECEIVE_ANALYSIS_GROUPS = 'RECEIVE_ANALYSIS_GROUPS'

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
  const { loadedProjectChildEntities } = getState()

  if (!(loadedProjectChildEntities[projectGuid] || {})[entityType]) {
    dispatch({ type: dispatchType })
    new HttpRequestHelper(`/api/project/${projectGuid}/get_${toSnakecase(entityType)}`,
      (responseJson) => {
        dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
        if (receiveDispatchType) {
          dispatch({ type: receiveDispatchType, updatesById: responseJson })
        }
        dispatch({ type: RECEIVE_PROJECT_CHILD_ENTITES, updatesById: { [projectGuid]: { [entityType]: true } } })
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

export const loadProjectDetails = projectGuid => (dispatch, getState) => {
  const project = getState().projectsByGuid[projectGuid]
  if (!project || project.canEdit === undefined) {
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

export const loadProjectAnalysisGroups = projectGuid => loadProjectChildEntities(
  projectGuid, 'analysis groups', REQUEST_ANALYSIS_GROUPS, RECEIVE_ANALYSIS_GROUPS,
)

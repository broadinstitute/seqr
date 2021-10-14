import { SubmissionError } from 'redux-form'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// actions
export const RECEIVE_DATA = 'RECEIVE_DATA'
export const REQUEST_PROJECTS = 'REQUEST_PROJECTS'
export const RECEIVE_SAVED_SEARCHES = 'RECEIVE_SAVED_SEARCHES'
export const REQUEST_SAVED_SEARCHES = 'REQUEST_SAVED_SEARCHES'
export const REQUEST_SAVED_VARIANTS = 'REQUEST_SAVED_VARIANTS'
export const REQUEST_SEARCHED_VARIANTS = 'REQUEST_SEARCHED_VARIANTS'
export const RECEIVE_SEARCHED_VARIANTS = 'RECEIVE_SEARCHED_VARIANTS'

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

// A helper method to load a project and all its detail fields
export const loadProjectDetails = (projectGuid, requestType = REQUEST_PROJECTS, detailField = 'variantTagTypes') => {
  return (dispatch, getState) => {
    const project = getState().projectsByGuid[projectGuid]
    if (!project || !project[detailField]) {
      dispatch({ type: requestType || REQUEST_PROJECTS })
      new HttpRequestHelper(`/api/project/${projectGuid}/details`,
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

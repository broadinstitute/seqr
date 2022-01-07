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
    },
    (e) => {
      throw new SubmissionError({ _error: [e.message] })
    }).post(values)
}

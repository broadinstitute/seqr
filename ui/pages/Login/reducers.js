import { SubmissionError } from 'redux-form'
import queryString from 'query-string'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const redirectNext = () => {
  // Redirect to next page or home page
  window.location.href = `${window.location.origin}${queryString.parse(window.location.search).next || ''}`
}

// Data actions

export const login = values => () => new HttpRequestHelper(
  '/api/login', redirectNext, (e) => {
    throw new SubmissionError({ _error: [e.message] })
  },
).post(values)

export const forgotPassword = values => () => new HttpRequestHelper(
  '/api/users/forgot_password',
  () => {},
  (e) => {
    throw new SubmissionError({ _error: [e.message] })
  },
).post(values)

export const setPassword = values => () => new HttpRequestHelper(
  `/api/users/${values.username}/set_password`,
  () => {
    // Redirect to home page
    window.location.href = window.location.origin
  },
  (e) => {
    throw new SubmissionError({ _error: [e.message] })
  },
).post(values)

export const updateUserPolicies = values => () => new HttpRequestHelper('/api/users/update_policies',
  redirectNext,
  (e) => {
    throw new SubmissionError({ _error: [e.message] })
  }).post(values)

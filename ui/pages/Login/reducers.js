import { SubmissionError } from 'redux-form'
import queryString from 'query-string'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// Data actions

export const login = (values) => {
  return () => {
    return new HttpRequestHelper('/api/login',
      () => {
        // Redirect to next page or home page
        window.location.href = `${window.location.origin}${queryString.parse(window.location.search).next || ''}`
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}

export const forgotPassword = (values) => {
  return () => {
    return new HttpRequestHelper('/api/users/forgot_password',
      () => {},
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}

export const setPassword = (values) => {
  return () => {
    return new HttpRequestHelper(`/api/users/${values.username}/set_password`,
      () => {
        // Redirect to home page
        window.location.href = window.location.origin
      },
      (e) => {
        throw new SubmissionError({ _error: [e.message] })
      },
    ).post(values)
  }
}

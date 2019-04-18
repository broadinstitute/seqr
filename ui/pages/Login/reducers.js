import { SubmissionError } from 'redux-form'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

// Data actions

export const setPassword = (values) => {
  return () => {
    return new HttpRequestHelper(`/api/users/${values.username}/set_password`,
      () => {
        // Redirect to home page
        window.location.href = window.location.origin
      },
      (e) => {
        if (e.body && e.body.errors) {
          throw new SubmissionError({ _error: e.body.errors })
        } else {
          throw new SubmissionError({ _error: [e.message] })
        }
      },
    ).post(values)
  }
}

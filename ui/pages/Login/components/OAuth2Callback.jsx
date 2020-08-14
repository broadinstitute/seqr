import React from 'react'
import PropTypes from 'prop-types'
import { SubmissionError } from 'redux-form'
import queryString from 'query-string'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const OAuth2Callback = ({ location }) => {
  // Send the authentication results to the backend to finish the logging-in procedure
  new HttpRequestHelper('/api/login_oauth2callback',
    () => {
      // Redirect to next page or home page
      window.location.href = `${window.location.origin}${queryString.parse(window.location.search).next || ''}`
    },
    (e) => {
      throw new SubmissionError({ _error: [e.message] })
    },
  ).post(location.pathname + location.search)
  return <div>Logging in with Google</div>
}

OAuth2Callback.propTypes = {
  location: PropTypes.object.isRequired,
}

export default OAuth2Callback

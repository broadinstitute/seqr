import React from 'react'
import { withRouter } from 'react-router'
import queryString from 'query-string'

const QueryParamEditor = ({ queryParam, history, location, children }) => {
  const updateQueryParam = value => history.push({ ...location, search: value ? `?${queryParam}=${value}` : null })
  const currentQueryParam = queryString.parse(location.search)[queryParam]

  return React.cloneElement(children, { updateQueryParam, currentQueryParam })
}

export default withRouter(QueryParamEditor)

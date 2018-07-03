import React from 'react'
import { withRouter } from 'react-router'
import queryString from 'query-string'

const QueryParamEditor = ({ queryParam, history, location, children }) => {
  let params = queryString.parse(location.search)
  const updateQueryParam = (value) => {
    if (value) {
      params = { ...params, [queryParam]: value }
    } else {
      delete params[queryParam]
    }
    history.push({ ...location, search: `?${queryString.stringify(params)}` })
  }

  return React.cloneElement(children, { updateQueryParam, currentQueryParam: params[queryParam] })
}

export { QueryParamEditor as QueryParamEditorComponent }
export default withRouter(QueryParamEditor)

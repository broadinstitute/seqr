import React from 'react'
import { withRouter } from 'react-router'
import queryString from 'query-string'

export const QueryParamsEditor = ({ history, location, children, ...props }) => {
  let params = queryString.parse(location.search)
  const updateQueryParams = (values) => {
    params = Object.entries(values).reduce((acc, [param, val]) => (val ? { ...acc, [param]: val } : acc), {})
    history.push({ ...location, search: `?${queryString.stringify(params)}` })
  }

  return React.cloneElement(children, { updateQueryParams, queryParams: params, ...props })
}

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

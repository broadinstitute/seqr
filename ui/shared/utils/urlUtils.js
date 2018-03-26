const env = process.env.NODE_ENV || 'development'

export const computeDashboardUrl = () => (
  env === 'development' ?
    '/app.html' :
    '/dashboard'
)

export const computeCaseReviewUrl = (projectGuid) => {
  if (env !== 'development') {
    return `/project/${projectGuid}/case_review`
  }
  return `/case_review.html?initialUrl=/api/project/${projectGuid}/case_review`
}

export const computeProjectUrl = (projectGuid) => {
  if (env !== 'development') {
    return `/project/${projectGuid}/project_page`
  }
  return `/app.html?projectGuid=${projectGuid}`
}

export const computeVariantSearchUrl = (projectGuid = null, familyGuid = null) => {

  let baseUrl = '/variant_search'
  if (familyGuid !== null) {
    baseUrl = `/family/${familyGuid}${baseUrl}`
  }

  if (projectGuid !== null) {
    baseUrl = `/project/${projectGuid}${baseUrl}`
  }

  if (env !== 'development') {
    return baseUrl
  }

  return `variant_search.html?initialUrl=/api${baseUrl}`
}

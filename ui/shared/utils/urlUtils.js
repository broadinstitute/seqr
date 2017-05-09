const env = process.env.NODE_ENV || 'development'

export const computeDashboardUrl = () => (
  env === 'development' ?
    '/dashboard.html' :
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
    return `/project/${projectGuid}/view`
  }
  return `/project.html?initialUrl=/api/project/${projectGuid}/view`
}


const env = process.env.NODE_ENV || 'development'

export const computeCaseReviewUrl = (projectGuid) => {
  if (env !== 'development') {
    return `/project/${projectGuid}/case_review`
  }
  return `/case_review.html?initialUrl=/api/project/${projectGuid}/case_review`
}

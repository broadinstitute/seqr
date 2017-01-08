import React from 'react'


const env = process.env.NODE_ENV || 'development'

const CaseReviewLink = (props) => {
  const url = (env !== 'development') ?
    `/project/${props.projectGuid}/case_review` :
    `/case_review.html?initialUrl=/api//project/${props.projectGuid}/case_review`

  return <a href={url}>Case Review</a>
}


CaseReviewLink.propTypes = {
  projectGuid: React.PropTypes.string.isRequired,
}

export default CaseReviewLink

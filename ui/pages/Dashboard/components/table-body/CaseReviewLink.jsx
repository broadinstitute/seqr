import React from 'react'
import { computeCaseReviewUrl } from '../../utils/urlUtils'

const CaseReviewLink = (props) => {
  return <a style={{ color: 'black' }} href={computeCaseReviewUrl(props.projectGuid)}>Case Review</a>
}

CaseReviewLink.propTypes = {
  projectGuid: React.PropTypes.string.isRequired,
}

export default CaseReviewLink

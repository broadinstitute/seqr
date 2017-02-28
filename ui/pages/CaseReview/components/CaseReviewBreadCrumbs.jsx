import React from 'react'

import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const CaseReviewBreadCrumbs = (props) => {
  return <BreadCrumbs
    breadcrumbSections={[
      <a href="/dashboard">Home</a>,
      <a href={`/project/${props.project.deprecatedProjectId}`}>{props.project.name}</a>,
      'Case Review',
    ]}
  />
}

CaseReviewBreadCrumbs.propTypes = {
  project: React.PropTypes.object.isRequired,
}

export default CaseReviewBreadCrumbs

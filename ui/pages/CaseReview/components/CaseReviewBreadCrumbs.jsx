import React from 'react'
import { connect } from 'react-redux'

import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const CaseReviewBreadCrumbs = (props) => {
  document.title = `Case Review: ${props.project.name}`

  return <BreadCrumbs
    breadcrumbSections={[
      <a href="/dashboard">Home</a>,
      <a href={`/project/${props.project.deprecatedProjectId}`}>{props.project.name}</a>,
      'Case Review',
    ]}
  />
}

export { CaseReviewBreadCrumbs as CaseReviewBreadCrumbsComponent }

CaseReviewBreadCrumbs.propTypes = {
  project: React.PropTypes.object.isRequired,
}

const mapStateToProps = ({ project }) => ({ project })

export default connect(mapStateToProps)(CaseReviewBreadCrumbs)

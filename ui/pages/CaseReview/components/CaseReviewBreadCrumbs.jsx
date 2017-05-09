import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import BreadCrumbs from 'shared/components/page/BreadCrumbs'
import { computeProjectUrl } from 'shared/utils/urlUtils'

const CaseReviewBreadCrumbs = (props) => {
  document.title = `Case Review: ${props.project.name}`

  return <BreadCrumbs
    breadcrumbSections={[
      <a href="/dashboard">Home</a>,
      <a href={computeProjectUrl(props.project.projectGuid)}>{props.project.name}</a>,
      'Case Review',
    ]}
  />
}

export { CaseReviewBreadCrumbs as CaseReviewBreadCrumbsComponent }

CaseReviewBreadCrumbs.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = ({ project }) => ({ project })

export default connect(mapStateToProps)(CaseReviewBreadCrumbs)

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import BreadCrumbs from 'shared/components/page/BreadCrumbs'
import { computeDashboardUrl, computeProjectUrl } from 'shared/utils/urlUtils'

const ProjectBreadCrumbs = (props) => {
  document.title = `Project: ${props.project.name}`

  return <BreadCrumbs
    breadcrumbSections={[
      <a href={computeDashboardUrl()}>Home</a>,
      <a href={computeProjectUrl(props.project.projectGuid)}>{props.project.name}</a>,
      'Project',
    ]}
  />
}

export { ProjectBreadCrumbs as ProjectBreadCrumbsComponent }

ProjectBreadCrumbs.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = ({ project }) => ({ project })

export default connect(mapStateToProps)(ProjectBreadCrumbs)

import React from 'react'

//const env = process.env.NODE_ENV || 'development'

const ProjectPageLink = (props) => {
  /*
  const url = (env !== 'development') ?
    `/project/${props.projectGuid}/case_review` :
    `/case_review.html?initialUrl=/api/project/${props.projectGuid}/case_review`
  */
  const url = `/project/${props.project.deprecatedProjectId}`
  return <a href={url}>{props.project.name}</a>
}

export { ProjectPageLink as ProjectPageLinkComponent }

ProjectPageLink.propTypes = {
  project: React.PropTypes.object.isRequired,
}

export default ProjectPageLink

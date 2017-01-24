import React from 'react'

//const env = process.env.NODE_ENV || 'development'

const FamilyPageLink = (props) => {
  const url = `/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}`
  return <a href={url}>{props.family.name}</a>
}

FamilyPageLink.propTypes = {
  project: React.PropTypes.object.isRequired,
  family: React.PropTypes.object.isRequired,
}

export default FamilyPageLink

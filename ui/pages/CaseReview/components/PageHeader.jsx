import React from 'react'

import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const PageHeader = (props) => {
  return <BreadCrumbs
    breadcrumbSections={[
      <span>Project: &nbsp;
        <a href={`/project/${props.project.deprecatedProjectId}`}>{props.project.name}</a>
      </span>,
      'Case Review',
    ]}
  />
}

PageHeader.propTypes = {
  project: React.PropTypes.object.isRequired,
}

export default PageHeader

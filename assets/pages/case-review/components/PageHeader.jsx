import React from 'react'
import DocumentTitle from 'react-document-title'

import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const PageHeader = (props) => {
  const projectName = props.project.projectName || props.project.projectId

  return <DocumentTitle title={`${projectName}: Case Review`}>
    <BreadCrumbs
      breadcrumbSections={[
        <span>
          Project: &nbsp;
          <a href={`/project/${props.project.projectId}`}>
            {projectName}
          </a>
        </span>,
        'Case Review',
      ]}
    />
  </DocumentTitle>
}

PageHeader.propTypes = {
  project: React.PropTypes.object.isRequired,
}

export default PageHeader

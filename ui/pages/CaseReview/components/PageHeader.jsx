import React from 'react'
import DocumentTitle from 'react-document-title'

import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const PageHeader = (props) => {
  return <DocumentTitle title={`${props.project.name}: Case Review`}>
    <BreadCrumbs
      breadcrumbSections={[
        <span>Project: &nbsp;
          <a href={`/project/${props.project.deprecatedProjectId}`}>{props.project.name}</a>
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

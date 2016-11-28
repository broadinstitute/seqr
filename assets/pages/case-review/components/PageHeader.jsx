import React from 'react'
import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const PageHeader = props => <div>
  <BreadCrumbs
    breadcrumbSections={[
      <span>
        Project: <a href={`/project/${props.project.projectId}`}>{props.project.projectName}</a>
      </span>,
      'Case Review',
    ]}
  /> <br />
</div>


PageHeader.propTypes = {
  project: React.PropTypes.object.isRequired,
}

export default PageHeader

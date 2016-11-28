import React from 'react'
import BreadCrumbs from '../../../shared/components/BreadCrumbs'

const PageHeader = ({ project }) => <div>
  <BreadCrumbs
    breadcrumbSections={[
      <span>{'Project: '}<a href={`/project/${project.project_id}`}>{project.project_id}</a></span>,
      'Case Review',
    ]}
  /> <br />
</div>


PageHeader.propTypes = {
  project: React.PropTypes.object.isRequired,
}

export default PageHeader

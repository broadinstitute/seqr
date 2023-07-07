import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import EditProjectButton from 'shared/components/buttons/EditProjectButton'
import PageHeaderLayout from 'shared/components/page/PageHeaderLayout'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { CONSENT_CODE_LOOKUP } from 'shared/utils/constants'

import {
  getCurrentProject,
  getPageHeaderEntityLinks,
  getPageHeaderBreadcrumbIdSections,
  getPageHeaderFamily,
  getPageHeaderAnalysisGroup,
} from '../selectors'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'

const PageHeader = React.memo((
  { project, family, analysisGroup, user, breadcrumb, match, breadcrumbIdSections, entityLinks },
) => {
  if (!project) {
    return null
  }

  let { description } = project
  let button = null
  if (match.params.breadcrumb === 'project_page') {
    button = <EditProjectButton project={project} user={user} />
    if (user.isPm && project.consentCode) {
      description = (
        <Header.Subheader>
          {description}
          <br />
          <i>
            Consent Code: &nbsp;
            {CONSENT_CODE_LOOKUP[project.consentCode]}
          </i>
        </Header.Subheader>
      )
    }
  } else if (match.params.breadcrumb === 'family_page') {
    const { breadcrumbIdSection } = match.params
    if (breadcrumbIdSection === 'matchmaker_exchange' || breadcrumbIdSection === 'rnaseq_results') {
      description = ''
    } else {
      description = family.description
    }
  } else if (match.params.breadcrumb === 'analysis_group') {
    description = analysisGroup.description
    button = (
      <span>
        <UpdateAnalysisGroupButton analysisGroup={analysisGroup} />
        <HorizontalSpacer width={10} />
        <DeleteAnalysisGroupButton analysisGroup={analysisGroup} />
      </span>
    )
  }

  const headerProps = breadcrumbIdSections ? { breadcrumbIdSections } : match.params

  return (
    <PageHeaderLayout
      entity="project"
      entityGuid={project.projectGuid}
      title={project.name}
      description={description}
      button={button}
      entityLinkPath={null}
      entityGuidLinkPath="project_page"
      breadcrumb={breadcrumb}
      entityLinks={entityLinks}
      {...headerProps}
    />
  )
})

PageHeader.propTypes = {
  project: PropTypes.object,
  family: PropTypes.object,
  analysisGroup: PropTypes.object,
  user: PropTypes.object,
  match: PropTypes.object,
  breadcrumb: PropTypes.string,
  breadcrumbIdSections: PropTypes.arrayOf(PropTypes.object),
  entityLinks: PropTypes.arrayOf(PropTypes.object),
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  family: getPageHeaderFamily(state, ownProps),
  analysisGroup: getPageHeaderAnalysisGroup(state, ownProps),
  user: getUser(state),
  breadcrumbIdSections: getPageHeaderBreadcrumbIdSections(state, ownProps),
  entityLinks: getPageHeaderEntityLinks(state, ownProps),
})

export default connect(mapStateToProps)(PageHeader)

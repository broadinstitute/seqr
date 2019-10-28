import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser, getFamiliesByGuid, getAnalysisGroupsByGuid, getCurrentProject } from 'redux/selectors'
import EditProjectButton from 'shared/components/buttons/EditProjectButton'
import { PageHeaderLayout } from 'shared/components/page/PageHeader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'

const familySearchEntityLink = family => ({
  to: `/variant_search/family/${family.familyGuid}`,
  text: 'Family Variant Search',
})

const analysisGroupSearchEntityLink = analysisGroup => ({
  to: `/variant_search/analysis_group/${analysisGroup.analysisGroupGuid}`,
  text: 'Analysis Group Search',
})

const PAGE_CONFIGS = {
  project_page: (match, project) => ({
    breadcrumbIdSections: [],
    button: <EditProjectButton project={project} />,
  }),
  family_page: (match, project, family) => {
    let { description } = family
    const breadcrumbIdSections = [{
      content: `Family: ${family.displayName}`,
      link: `/project/${project.projectGuid}/family_page/${family.familyGuid}`,
    }]
    if (match.params.breadcrumbIdSection) {
      breadcrumbIdSections.push({ content: snakecaseToTitlecase(match.params.breadcrumbIdSection), link: match.url })
      if (match.params.breadcrumbIdSection === 'matchmaker_exchange') {
        description = ''
      }
    }

    return {
      breadcrumbIdSections,
      description,
      entityLinks: [familySearchEntityLink(family)],
    }
  },
  analysis_group: (match, project, family, analysisGroup) => ({
    breadcrumbIdSections: [{ content: `Analysis Group: ${analysisGroup.name}`, link: match.url }],
    description: analysisGroup.description,
    entityLinks: [analysisGroupSearchEntityLink(analysisGroup)],
    button: (
      <span>
        <UpdateAnalysisGroupButton analysisGroup={analysisGroup} />
        <HorizontalSpacer width={10} />
        <DeleteAnalysisGroupButton analysisGroup={analysisGroup} />
      </span>
    ),
  }),
  saved_variants: (match, project, family, analysisGroup) => {
    const { variantPage, tag } = match.params
    const path = `/project/${project.projectGuid}/saved_variants`
    const breadcrumbIdSections = [{ content: 'Saved Variants', link: path }]
    const entityLinks = []
    if (variantPage === 'variant') {
      breadcrumbIdSections.push({ content: 'Variant', link: match.url })
    } else if (variantPage === 'family') {
      breadcrumbIdSections.push({ content: `Family: ${family.displayName}`, link: `${path}/family/${family.familyGuid}` })
      entityLinks.push(familySearchEntityLink(family))
      if (tag) {
        breadcrumbIdSections.push({ content: tag, link: `${path}/family/${family.familyGuid}/${tag}` })
      }
    } else if (variantPage === 'analysis_group') {
      breadcrumbIdSections.push({ content: `Analysis Group: ${analysisGroup.name}`, link: `${path}/analysis_group/${analysisGroup.analysisGroupGuid}` })
      entityLinks.push(analysisGroupSearchEntityLink(analysisGroup))
      if (tag) {
        breadcrumbIdSections.push({ content: tag, link: `${path}/analysis_group/${analysisGroup.analysisGroupGuid}/${tag}` })
      }
    } else if (variantPage) {
      breadcrumbIdSections.push({ content: variantPage, link: match.url })
    }
    return {
      breadcrumb: 'saved_variants',
      breadcrumbIdSections,
      entityLinks,
    }
  },
}


const PageHeader = ({ user, project, family, analysisGroup, breadcrumb, match }) => {

  if (!project) {
    return null
  }

  breadcrumb = breadcrumb || match.params.breadcrumb

  const headerProps = PAGE_CONFIGS[breadcrumb] ?
    PAGE_CONFIGS[breadcrumb](match, project, family, analysisGroup) :
    { breadcrumb, breadcrumbId: match.params.breadcrumbId }

  const entityLinks = (headerProps.entityLinks || [])
  if (entityLinks.length === 0) {
    entityLinks.push({ to: `/variant_search/project/${project.projectGuid}`, text: 'Project Variant Search' })
  }
  if (user.isStaff && breadcrumb !== 'case_review') {
    entityLinks.push({ to: `/project/${project.projectGuid}/case_review`, text: 'Case Review' })
  }

  return (
    <PageHeaderLayout
      entity="project"
      entityGuid={project.projectGuid}
      title={project.name}
      description={project.description}
      entityLinkPath={null}
      entityGuidLinkPath="project_page"
      {...headerProps}
      entityLinks={entityLinks}
    />
  )
}

PageHeader.propTypes = {
  user: PropTypes.object,
  project: PropTypes.object,
  family: PropTypes.object,
  analysisGroup: PropTypes.object,
  match: PropTypes.object,
  breadcrumb: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  user: getUser(state),
  project: getCurrentProject(state),
  family: getFamiliesByGuid(state)[ownProps.match.params.breadcrumbId] || {},
  analysisGroup: getAnalysisGroupsByGuid(state)[ownProps.match.params.breadcrumbId] || {},
})

export default connect(mapStateToProps)(PageHeader)

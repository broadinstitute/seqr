import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser, getFamiliesByGuid, getAnalysisGroupsByGuid } from 'redux/selectors'
import EditProjectButton from 'shared/components/buttons/EditProjectButton'
import { PageHeaderLayout } from 'shared/components/page/PageHeader'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'
import { getProject } from '../selectors'

const ORIGINAL_PROJECT_PAGE_CONFIG = { name: 'Project', path: '' }

const familySearchEntityLink = (project, family) => ({
  to: project.hasNewSearch && `/variant_search/family/${family.familyGuid}`,
  href: !project.hasNewSearch && `/project/${project.deprecatedProjectId}/family/${family.familyId}/mendelian-variant-search`,
  text: 'Family Variant Search',
})

const analysisGroupSearchEntityLink = (project, analysisGroup) => ({
  to: project.hasNewSearch && `/variant_search/analysis_group/${analysisGroup.analysisGroupGuid}`,
  href: !project.hasNewSearch && `/project/${project.deprecatedProjectId}/family-group/guid/${analysisGroup.analysisGroupGuid}/combine-mendelian-families`,
  text: 'Analysis Group Search',
})

const PAGE_CONFIGS = {
  project_page: () => ({
    breadcrumbIdSections: [],
    originalPages: [ORIGINAL_PROJECT_PAGE_CONFIG, { name: 'Families', path: 'families' }],
  }),
  family_page: (match, project, family) => ({
    breadcrumbIdSections: [{ content: `Family: ${family.displayName}`, link: match.url }],
    description: family.description,
    originalPages: [{ name: 'Family', path: `family/${family.familyId}` }],
    entityLinks: [familySearchEntityLink(project, family)],
  }),
  analysis_group: (match, project, family, analysisGroup) => ({
    breadcrumbIdSections: [{ content: `Analysis Group: ${analysisGroup.name}`, link: match.url }],
    description: analysisGroup.description,
    originalPages: [{ name: 'Analysis Group', path: `family-group/guid/${analysisGroup.analysisGroupGuid}/` }],
    entityLinks: [analysisGroupSearchEntityLink(project, analysisGroup)],
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
    let originalPagePath = 'saved-variants'
    const breadcrumbIdSections = [{ content: 'Saved Variants', link: path }]
    const entityLinks = []
    if (variantPage === 'variant') {
      originalPagePath = null
      breadcrumbIdSections.push({ content: 'Variant', link: match.url })
    } else if (variantPage === 'family') {
      breadcrumbIdSections.push({ content: `Family: ${family.displayName}`, link: `${path}/family/${family.familyGuid}` })
      entityLinks.push(familySearchEntityLink(project, family))
      if (tag) {
        breadcrumbIdSections.push({ content: tag, link: `${path}/family/${family.familyGuid}/${tag}` })
        originalPagePath = `variants/${tag}?family=${family.familyId}`
      } else {
        originalPagePath = `saved-variants?family=${family.familyId}`
      }
    } else if (variantPage === 'analysis_group') {
      breadcrumbIdSections.push({ content: `Analysis Group: ${analysisGroup.name}`, link: `${path}/analysis_group/${analysisGroup.analysisGroupGuid}` })
      entityLinks.push(analysisGroupSearchEntityLink(project, analysisGroup))
      if (tag) {
        breadcrumbIdSections.push({ content: tag, link: `${path}/analysis_group/${analysisGroup.analysisGroupGuid}/${tag}` })
        originalPagePath = `variants/${tag}`
      } else {
        originalPagePath = 'saved-variants'
      }
    } else if (variantPage) {
      originalPagePath = `variants/${variantPage}`
      breadcrumbIdSections.push({ content: variantPage, link: match.url })
    }
    return {
      breadcrumb: 'saved_variants',
      originalPages: originalPagePath ? [{ name: 'Saved Variants', path: originalPagePath }] : [],
      breadcrumbIdSections,
      entityLinks,
    }
  },
}


export const PageHeader = ({ user, project, family, analysisGroup, breadcrumb, match }) => {

  if (!project) {
    return null
  }

  breadcrumb = breadcrumb || match.params.breadcrumb

  const headerProps = PAGE_CONFIGS[breadcrumb] ?
    PAGE_CONFIGS[breadcrumb](match, project, family, analysisGroup) :
    { breadcrumb, breadcrumbId: match.params.breadcrumbId, originalPages: [ORIGINAL_PROJECT_PAGE_CONFIG] }

  const entityLinks = (headerProps.entityLinks || [])
  if (project.hasNewSearch && entityLinks.length === 0) {
    entityLinks.push({ to: `/variant_search/project/${project.projectGuid}`, text: 'Project Variant Search' })
  }
  if (project.hasGeneSearch) {
    if (project.hasNewSearch) {
      if (!headerProps.originalPages) {
        headerProps.originalPages = []
      }
      headerProps.originalPages.push({ path: 'gene', name: 'Gene Search' })
    } else {
      entityLinks.push({ href: `/project/${project.deprecatedProjectId}/gene`, text: 'Gene Search' })
    }
  }
  if (user.is_staff && breadcrumb !== 'case_review') {
    entityLinks.push({ to: `/project/${project.projectGuid}/case_review`, text: 'Case Review' })
  }

  return (
    <PageHeaderLayout
      entity="project"
      entityGuid={project.projectGuid}
      title={project.name}
      description={project.description}
      button={<EditProjectButton project={project} />}
      entityLinkPath={null}
      entityGuidLinkPath="project_page"
      originalPagePath={`project/${project.deprecatedProjectId}`}
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
  project: getProject(state),
  family: getFamiliesByGuid(state)[ownProps.match.params.breadcrumbId] || {},
  analysisGroup: getAnalysisGroupsByGuid(state)[ownProps.match.params.breadcrumbId] || {},
})

export default connect(mapStateToProps)(PageHeader)

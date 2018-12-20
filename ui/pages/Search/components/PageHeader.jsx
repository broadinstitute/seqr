import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProjectsByGuid, getFamiliesByGuid, getAnalysisGroupsByGuid } from 'redux/selectors'
import { PageHeaderLayout } from 'shared/components/page/PageHeader'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { getSelectedAnalysisGroups } from '../constants'
import { getSearchesByHash } from '../selectors'


const PAGE_CONFIGS = {
  project: (entityGuid, projectsByGuid) => ({
    entity: projectsByGuid[entityGuid],
    entityUrlPath: 'project_page',
  }),
  family: (entityGuid, projectsByGuid, familiesByGuid) => ({
    entity: familiesByGuid[entityGuid],
    entityUrlPath: `family_page/${entityGuid}`,
    originalPagePath: familiesByGuid[entityGuid] && `family/${familiesByGuid[entityGuid].familyId}/mendelian-variant-search`,
  }),
  analysis_group: (entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid) => ({
    entity: analysisGroupsByGuid[entityGuid],
    entityUrlPath: `analysis_group/${entityGuid}`,
    originalPagePath: `family-group/guid/${entityGuid}/combine-mendelian-families`,
  }),
  results: () => ({}),
}


export const PageHeader = ({ projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash, match }) => {

  let { pageType, entityGuid } = match.params

  if (pageType === 'results') {
    const { searchedProjectFamilies } = searchesByHash[entityGuid] || {}
    if (searchedProjectFamilies) {
      if (searchedProjectFamilies.length === 1) {
        const { projectGuid, familyGuids } = searchedProjectFamilies[0]
        if (familyGuids.length === 1) {
          pageType = 'family'
          entityGuid = familyGuids[0] //eslint-disable-line prefer-destructuring
        } else {
          const analysisGroups = getSelectedAnalysisGroups(analysisGroupsByGuid, familyGuids)
          if (analysisGroups.length === 1 && analysisGroups[0].familyGuids.length === familyGuids.length) {
            pageType = 'analysis_group'
            entityGuid = analysisGroups[0].analysisGroupGuid
          } else {
            pageType = 'project'
            entityGuid = projectGuid
          }
        }
      }
      // TODO parse multi-project search
    }
  }

  let project
  let originalPages
  const breadcrumbIdSections = []
  const { entity, entityUrlPath, originalPagePath } = PAGE_CONFIGS[pageType](entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid)
  if (entity) {
    project = projectsByGuid[entity.projectGuid]
    breadcrumbIdSections.push({ content: snakecaseToTitlecase(pageType) })
    breadcrumbIdSections.push({ content: entity.displayName || entity.name, link: `/project/${entity.projectGuid}/${entityUrlPath}` })
    if (originalPagePath) {
      originalPages = [{ path: originalPagePath }]
    }
  }

  const entityLinks = []
  if (project && project.hasGeneSearch) {
    entityLinks.push({ href: `/project/${project.deprecatedProjectId}/gene`, text: 'Gene Search' })
  }

  return (
    <PageHeaderLayout
      entity="variant_search"
      entityLinkPath={null} // TODO remove this to enable main page link once multi-project search is enabled
      breadcrumbIdSections={breadcrumbIdSections}
      description={null} // TODO add description for multi-project searches
      originalPagePath={project && `project/${project.deprecatedProjectId}`}
      originalPages={originalPages}
      entityLinks={entityLinks}
    />
  )
}

PageHeader.propTypes = {
  projectsByGuid: PropTypes.object,
  familiesByGuid: PropTypes.object,
  analysisGroupsByGuid: PropTypes.object,
  searchesByHash: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  projectsByGuid: getProjectsByGuid(state),
  familiesByGuid: getFamiliesByGuid(state),
  analysisGroupsByGuid: getAnalysisGroupsByGuid(state),
  searchesByHash: getSearchesByHash(state),
})

export default connect(mapStateToProps)(PageHeader)

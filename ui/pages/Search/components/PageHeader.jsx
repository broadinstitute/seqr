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
  results: (entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash) => {
    const { projectFamilies } = searchesByHash[entityGuid] || {}
    let pageType
    let description
    if (projectFamilies) {
      if (projectFamilies.length === 1) {
        const { projectGuid, familyGuids } = projectFamilies[0]
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
      } else if (projectFamilies.length > 1) {
        description = `Projects: ${projectFamilies.map(
          ({ projectGuid }) => (projectsByGuid[projectGuid] || {}).name,
        ).filter(val => val).join(', ')}`
      }
    }
    if (pageType) {
      return {
        actualPageType: pageType,
        ...PAGE_CONFIGS[pageType](entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid),
      }
    }
    return { description }
  },
  variant: entityGuid => ({ entity: { name: entityGuid } }),
}


export const PageHeader = ({ projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash, match }) => {

  const { pageType, entityGuid } = match.params

  let project
  let originalPages
  const breadcrumbIdSections = []
  const { entity, entityUrlPath, originalPagePath, actualPageType, description } =
    PAGE_CONFIGS[pageType](entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash)
  if (entity) {
    project = projectsByGuid[entity.projectGuid]
    breadcrumbIdSections.push({ content: snakecaseToTitlecase(actualPageType || pageType) })
    breadcrumbIdSections.push({
      content: entity.displayName || entity.name,
      link: project && `/project/${project.projectGuid}/${entityUrlPath}`,
    })
    if (originalPagePath) {
      originalPages = [{ path: originalPagePath }]
    }
  }

  if (project) {
    if (!originalPages) {
      originalPages = []
    }
    originalPages.push({ path: 'gene', name: 'Gene Search' })
  }

  return (
    <PageHeaderLayout
      entity="variant_search"
      breadcrumbIdSections={breadcrumbIdSections}
      description={description}
      originalPagePath={project && `project/${project.deprecatedProjectId}`}
      originalPages={originalPages}
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

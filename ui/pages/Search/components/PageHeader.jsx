import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProjectsByGuid, getFamiliesByGuid, getAnalysisGroupsByGuid, getSearchesByHash } from 'redux/selectors'
import PageHeaderLayout from 'shared/components/page/PageHeaderLayout'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { getSelectedAnalysisGroups } from '../constants'

const PAGE_CONFIGS = {
  project: (entityGuid, projectsByGuid) => ({
    entity: projectsByGuid[entityGuid],
    entityUrlPath: 'project_page',
  }),
  family: (entityGuid, projectsByGuid, familiesByGuid) => ({
    entity: familiesByGuid[entityGuid],
    entityUrlPath: `family_page/${entityGuid}`,
  }),
  analysis_group: (entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid) => ({
    entity: analysisGroupsByGuid[entityGuid],
    entityUrlPath: `analysis_group/${entityGuid}`,
  }),
  families: entityGuid => ({ description: `Searching in ${entityGuid.split(/[,:]/).length} Families` }),
  results: (entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash) => {
    const { projectFamilies } = searchesByHash[entityGuid] || {}
    let pageType
    let description
    let specificEntityGuid = entityGuid
    if (projectFamilies) {
      if (projectFamilies.length === 1) {
        const { projectGuid, familyGuids } = projectFamilies[0]
        if (familyGuids.length === 1) {
          pageType = 'family'
          specificEntityGuid = familyGuids[0] // eslint-disable-line prefer-destructuring
        } else {
          const analysisGroups = getSelectedAnalysisGroups(analysisGroupsByGuid, familyGuids)
          if (analysisGroups.length === 1 && analysisGroups[0].familyGuids.length === familyGuids.length) {
            pageType = 'analysis_group'
            specificEntityGuid = analysisGroups[0].analysisGroupGuid
          } else {
            pageType = 'project'
            specificEntityGuid = projectGuid
          }
        }
      } else if (projectFamilies.length > 20) {
        description = `${projectFamilies.length} Projects`
      } else if (projectFamilies.length > 1) {
        description = `Projects: ${projectFamilies.map(
          ({ projectGuid }) => (projectsByGuid[projectGuid] || {}).name,
        ).filter(val => val).join(', ')}`
      }
    }
    if (pageType) {
      return {
        actualPageType: pageType,
        ...PAGE_CONFIGS[pageType](specificEntityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid),
      }
    }
    return { description }
  },
  variant: entityGuid => ({ entity: { name: entityGuid } }),
}

const getPageHeaderProps = ({ projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash, match }) => {
  const { pageType, entityGuid } = match.params

  const breadcrumbIdSections = []
  const { entity, entityUrlPath, actualPageType, description } =
    PAGE_CONFIGS[pageType](entityGuid, projectsByGuid, familiesByGuid, analysisGroupsByGuid, searchesByHash)
  if (entity) {
    const project = projectsByGuid[entity.projectGuid]
    breadcrumbIdSections.push({ content: snakecaseToTitlecase(actualPageType || pageType) })
    breadcrumbIdSections.push({
      content: entity.displayName || entity.name,
      link: project && `/project/${project.projectGuid}/${entityUrlPath}`,
    })
  }

  return { description, breadcrumbIdSections }
}

export const PageHeader = React.memo(
  props => <PageHeaderLayout entity="variant_search" entityLinkPath={null} {...getPageHeaderProps(props)} />,
)

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

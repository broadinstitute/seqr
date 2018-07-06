import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid, Breadcrumb } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

import { getUser, getFamiliesByGuid } from 'redux/selectors'
import { getProject } from 'pages/Project/selectors'
import EditProjectButton from '../buttons/EditProjectButton'
import { snakecaseToTitlecase } from '../../utils/stringUtils'


const PageHeaderRow = styled(Grid.Row)`
  padding: 9px;
  background-color: #F7F7F7;
  max-height: 200px;
  border-bottom: 1px solid #EEEEEE;
`

const BreadcrumbContainer = styled.div`
  margin: 50px 0px 25px 0px;
  
  .section {
    margin-bottom: 10px !important;
  }
  
  a.active {
    color: #111 !important;
    cursor: auto !important;
  }
`
const NavLinkNoActive = styled(NavLink)`
  &.active {
    display: none;
  }
`

const ENTITY_DETAILS = {
  project: (user, project) => (project ? {
    entityTitle: 'Project',
    title: project.name,
    description: project.description,
    entityGuidLink: 'project_page',
    originalPageLink: `project/${project.deprecatedProjectId}`,
    entityLinks: [
      project.hasGeneSearch ?
        <a key="gene" href={`/project/${project.deprecatedProjectId}/gene`}><br />Gene Search<br /></a> : null,
      user.is_staff ?
        <NavLinkNoActive key="case_review" to={`/project/${project.projectGuid}/case_review`}>Case Review<br /></NavLinkNoActive> : null,
    ],
  } : null),
  gene_lists: () => ({
    entityTitle: 'Gene Lists',
    description: 'This page shows all of the gene lists that are available in your account',
    originalPageLink: 'gene-lists',
  }),
}

const PageHeader = ({ user, project, familiesByGuid, match }) => {

  const { entity, entityGuid, breadcrumb, breadcrumbId } = match.params
  const entityConfig = ENTITY_DETAILS[entity] && ENTITY_DETAILS[entity](user, project)
  if (!entityConfig) {
    return null
  }
  const { entityTitle, title, description, entityGuidLink, entityLinks, originalPageLink } = entityConfig

  let originalPageLinkPath
  const BREADCRUMBS = {
    project_page: {
      breadcrumbText: false,
      originalPages: [{ name: 'Project', path: '' }, { name: 'Families', path: 'families' }],
    },
    family_page: {
      breadcrumbText: false,
      breadcrumbIdParsers: [
        (breadcrumbIdSection) => {
          const { familyId } = familiesByGuid[breadcrumbIdSection] || {}
          originalPageLinkPath = `family/${familyId}`
          return { content: `Family: ${familyId || breadcrumbIdSection}`, link: match.url }
        },
      ],
      originalPages: [{ name: 'Family' }],
    },
    saved_variants: {
      breadcrumbIdParsers: [
        (breadcrumbIdSection) => {
          if (breadcrumbIdSection === 'family' || breadcrumbIdSection === 'variant') { return { content: null } }
          originalPageLinkPath = `variants/${breadcrumbIdSection}`
          return null
        },
        (breadcrumbIdSection) => {
          if (breadcrumbIdSection.startsWith('SV')) {
            originalPageLinkPath = false
            return { content: 'Variant', link: match.url }
          }
          const { familyId } = familiesByGuid[breadcrumbIdSection] || {}
          originalPageLinkPath = `saved-variants?family=${familyId}`
          return {
            content: `Family: ${familyId || breadcrumbIdSection}`,
            link: `/project/${project.projectGuid}/saved_variants/family/${breadcrumbIdSection}`,
          }
        },
        (breadcrumbIdSection) => {
          originalPageLinkPath = `variants/${breadcrumbIdSection}?${originalPageLinkPath.split('?')[1]}`
          return null
        },
      ],
      originalPages: [{ path: 'saved-variants' }],
    },
  }

  const {
    breadcrumbText = snakecaseToTitlecase(breadcrumb),
    breadcrumbIdParsers = [],
    originalPages = [{ path: '' }],
  } = BREADCRUMBS[breadcrumb] || {}

  let breadcrumbSections = [
    { content: entityTitle },
  ]
  if (entityGuid) {
    breadcrumbSections.push(
      { content: title, link: `/${entity}/${entityGuid}${entityGuidLink ? `/${entityGuidLink}` : ''}` },
    )
  }
  if (breadcrumb && breadcrumbText !== false) {
    breadcrumbSections.push({
      content: breadcrumbText,
      link: `/${entity}/${entityGuid}/${breadcrumb}`,
    })
  }
  if (breadcrumbId) {
    const breadcrumbIds = breadcrumbId.split('/')
    breadcrumbSections = breadcrumbSections.concat(breadcrumbIds.map((breadcrumbIdSection, i) => {
      const defaultIdBreadcrumb = {
        content: breadcrumbIdSection,
        link: `/${entity}/${entityGuid}/${breadcrumb}/${breadcrumbIds.slice(0, i + 1).join('/')}`,
      }
      return breadcrumbIdParsers[i] ? breadcrumbIdParsers[i](breadcrumbIdSection) || defaultIdBreadcrumb : defaultIdBreadcrumb
    }))
  }

  const breadcrumbs = breadcrumbSections.reduce(
    (acc, sectionConfig, i, { length }) => {
      if (!sectionConfig.content) {
        return acc
      }
      const sectionProps = sectionConfig.link ?
        { as: NavLink, to: sectionConfig.link, exact: true } : {}
      const section =
        <Breadcrumb.Section key={sectionConfig.content} {...sectionProps} content={sectionConfig.content} />
      if (i && i < length) {
        return [...acc, <Breadcrumb.Divider key={`divider${sectionConfig.content}`} icon="angle double right" />, section]
      }
      return [...acc, section]
    }, [],
  )
  return (
    <PageHeaderRow>
      <DocumentTitle key="title" title={`${breadcrumb || 'seqr'}: ${title || entityTitle}`} />
      <Grid.Column width={1} />
      <Grid.Column width={11}>
        <BreadcrumbContainer>
          <Breadcrumb size="massive">
            {breadcrumbs}
          </Breadcrumb>
        </BreadcrumbContainer>
        {
          description &&
          <div style={{ fontWeight: 300, fontSize: '16px', margin: '0px 30px 20px 5px', display: 'inline-block' }}>
            {description}
          </div>
        }
        {project && <EditProjectButton />}
      </Grid.Column>
      <Grid.Column width={3}>
        {entityLinks && <b>{entityLinks}</b>}
        <br />
        {originalPageLinkPath !== false && originalPages.map(page =>
          <a
            key={page.name || breadcrumb}
            href={`/${originalPageLink}/${originalPageLinkPath || page.path}`}
          >
            Deprecated {page.name || breadcrumbText || entityTitle} Page<br />
          </a>,
        )}
        <br />
      </Grid.Column>
      <Grid.Column width={1} />
    </PageHeaderRow>
  )
}

PageHeader.propTypes = {
  user: PropTypes.object,
  project: PropTypes.object,
  familiesByGuid: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
})

export default connect(mapStateToProps, null, null, { pure: false })(PageHeader)


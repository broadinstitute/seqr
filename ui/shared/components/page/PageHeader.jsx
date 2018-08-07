import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid, Breadcrumb } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

import { getUser, getFamiliesByGuid, getGenesById, getLocusListsByGuid } from 'redux/selectors'
import { getProject } from 'pages/Project/selectors'
import EditProjectButton from '../buttons/EditProjectButton'
import { CreateLocusListButton, DeleteLocusListButton } from '../buttons/LocusListButtons'
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
  dashboard: () => false,
  project: (entityGuid, user, project) => (project ? {
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
    button: <EditProjectButton />,
  } : null),
  gene_lists: (entityGuid, user, project, genesById, locusListsByGuid) => (
    (entityGuid && !locusListsByGuid[entityGuid]) ? false : {
      title: entityGuid && locusListsByGuid[entityGuid].name,
      entityLink: '/gene_lists',
      description: !entityGuid && 'This page shows all of the gene lists that are available in your account',
      originalPageLink: entityGuid ? `gene-lists/${entityGuid}?guid=true` : 'gene-lists',
      button: entityGuid ? <DeleteLocusListButton locusList={locusListsByGuid[entityGuid]} /> : <CreateLocusListButton />,
    }
  ),
  gene_info: (entityGuid, user, project, genesById) => ({
    title: entityGuid && (genesById[entityGuid] ? genesById[entityGuid].symbol : entityGuid),
    entityLink: '/gene_info',
    originalPageLink: `gene/${entityGuid || ''}`,
  }),
}

const PageHeader = ({ user, project, familiesByGuid, genesById, locusListsByGuid, match }) => {

  const { entity, entityGuid, breadcrumb, breadcrumbId } = match.params
  const entityConfig = ENTITY_DETAILS[entity] ? ENTITY_DETAILS[entity](entityGuid, user, project, genesById, locusListsByGuid) : {}
  if (!entityConfig) {
    return null
  }
  const { title, description, entityLink, entityGuidLink, entityLinks, originalPageLink, button } = entityConfig

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
    { content: snakecaseToTitlecase(entity), link: entityLink },
  ]
  if (entityGuid) {
    breadcrumbSections.push(
      { content: title || entityGuid, link: `/${entity}/${entityGuid}${entityGuidLink ? `/${entityGuidLink}` : ''}` },
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
      <DocumentTitle key="title" title={`${breadcrumb || 'seqr'}: ${title || snakecaseToTitlecase(entity)}`} />
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
        {button}
      </Grid.Column>
      <Grid.Column width={3}>
        {entityLinks && <b>{entityLinks}</b>}
        <br />
        {originalPageLink && originalPageLinkPath !== false && originalPages.map((page) => {
          const linkTitle = page.name || breadcrumbText || snakecaseToTitlecase(entity)
          const linkPath = originalPageLinkPath || page.path
          return (
            <a key={linkTitle} href={`/${originalPageLink}${linkPath ? '/' : ''}${linkPath}`}>
              Deprecated {linkTitle} Page <br />
            </a>
          )
        })}
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
  genesById: PropTypes.object,
  locusListsByGuid: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
  genesById: getGenesById(state),
  locusListsByGuid: getLocusListsByGuid(state),
})

export default connect(mapStateToProps, null, null, { pure: false })(PageHeader)


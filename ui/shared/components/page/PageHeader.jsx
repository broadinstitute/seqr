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


const PageHeaderRow = styled(Grid.Row)`
  padding: 9px;
  background-color: #F7F7F7;
  max-height: 200px;
  border-bottom: 1px solid #EEEEEE;
`

const BreadcrumbContainer = styled.div`
  margin: 50px 0px 35px 0px;
  
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

const PageHeader = ({ user, project, familiesByGuid, match }) => {
  if (!project || !match) {
    return null
  }

  let originalPageLink
  const BREADCRUMBS = {
    project_page: {
      breadcrumb: false,
      originalPages: [{ name: 'Project', path: '' }, { name: 'Families', path: 'families' }],
    },
    saved_variants: {
      breadcrumbIdParsers: [
        (breadcrumbId) => {
          if (breadcrumbId === 'family' || breadcrumbId === 'variant') { return { content: null } }
          originalPageLink = `variants/${breadcrumbId}`
          return null
        },
        (breadcrumbId) => {
          if (breadcrumbId.startsWith('SV')) {
            originalPageLink = false
            return { content: 'Variant', link: match.url }
          }
          const { familyId } = familiesByGuid[breadcrumbId] || {}
          originalPageLink = `saved-variants?family=${familyId}`
          return {
            content: `Family: ${familyId || breadcrumbId}`,
            link: `/project/${project.projectGuid}/saved_variants/family/${breadcrumbId}`,
          }
        },
        (breadcrumbId) => {
          originalPageLink = `variants/${breadcrumbId}?${originalPageLink.split('?')[1]}`
          return null
        },
      ],
      originalPages: [{ path: 'saved-variants' }],
    },
  }

  const {
    breadcrumb = match.params.breadcrumb.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' '),
    breadcrumbIdParsers = [],
    originalPages = [],
  } = BREADCRUMBS[match.params.breadcrumb] || {}

  let breadcrumbSections = [
    { content: 'Project' },
    { content: project.name, link: `/project/${project.projectGuid}/project_page` },
  ]
  if (breadcrumb !== false) {
    breadcrumbSections.push({
      content: breadcrumb,
      link: `/project/${project.projectGuid}/${match.params.breadcrumb}`,
    })
  }
  if (match.params.breadcrumbId) {
    const breadcrumbIds = match.params.breadcrumbId.split('/')
    breadcrumbSections = breadcrumbSections.concat(breadcrumbIds.map((breadcrumbId, i) => {
      const defaultIdBreadcrumb = {
        content: breadcrumbId,
        link: `/project/${project.projectGuid}/${match.params.breadcrumb}/${breadcrumbIds.slice(0, i + 1).join('/')}`,
      }
      return breadcrumbIdParsers[i] ? breadcrumbIdParsers[i](breadcrumbId) || defaultIdBreadcrumb : defaultIdBreadcrumb
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
      <DocumentTitle key="title" title={`${breadcrumb || 'seqr'}: ${project.name}`} />
      <Grid.Column width={1} />
      <Grid.Column width={11}>
        <BreadcrumbContainer>
          <Breadcrumb size="massive">
            {breadcrumbs}
          </Breadcrumb>
        </BreadcrumbContainer>
        {
          project.description &&
          <div style={{ fontWeight: 300, fontSize: '16px', margin: '0px 30px 20px 5px', display: 'inline-block' }}>
            {project.description}
          </div>
        }
        <EditProjectButton />
      </Grid.Column>
      <Grid.Column width={3}>
        {
          project.hasGeneSearch &&
          <b><a href={`/project/${project.deprecatedProjectId}/gene`}><br />Gene Search<br /></a></b>
        }
        {
          user.is_staff &&
            <NavLinkNoActive to={`/project/${project.projectGuid}/case_review`}>
              <b>Case Review</b><br />
            </NavLinkNoActive>
        }
        <br />
        {originalPageLink !== false && originalPages.map(page =>
          <a
            key={page.name || match.params.breadcrumb}
            href={`/project/${project.deprecatedProjectId}/${originalPageLink || page.path}`}
          >
            Original {page.name || breadcrumb} Page<br />
          </a>,
        )}
        <br />
        <a href="/gene-lists">Gene Lists</a><br />
        <a href="/gene">Gene Summary Information</a><br />
        {/*<a href={computeVariantSearchUrl(props.project.projectGuid)}>Variant Search</a>*/}
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


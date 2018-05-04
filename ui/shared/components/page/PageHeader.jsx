import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid, Breadcrumb } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

import { getUser, getFamiliesByGuid } from 'redux/rootReducer'
import { getProject } from 'pages/Project/reducers'
import EditProjectButton from '../buttons/EditProjectButton'


const PageHeaderRow = styled(Grid.Row)`
  padding: 9px;
  background-color: #F7F7F7;
  max-height: 200px;
  border-bottom: 1px solid #EEEEEE;
`

const BreadcrumbContainer = styled.div`
  margin: 50px 0px 35px 0px;
`

const PageHeader = ({ user, project, familiesByGuid, match }) => {
  if (!project || !match) {
    return null
  }

  const BREADCRUMBS = {
    project_page: {
      breadcrumb: false,
      originalPages: [{ name: 'Project', path: '' }, { name: 'Families', path: 'families' }],
    },
    saved_variants: {
      breadcrumbIdParsers: [
        (breadcrumbId) => { return breadcrumbId === 'family' ? { content: null } : null },
        (breadcrumbId) => { return {
          content: `Family: ${(familiesByGuid[breadcrumbId] || {}).familyId || breadcrumbId}`,
          link: `/project/${project.projectGuid}/saved_variants/family/${breadcrumbId}`,
        } },
      ],
      originalPages: [{ path: 'saved-variants', idPath: 'variants' }],
    },
  }

  const { breadcrumb, breadcrumbIdParsers = [], originalPages = [] } = BREADCRUMBS[match.params.breadcrumb] || {}
  let breadcrumbSections = [
    { content: 'Project' },
    { content: project.name, link: `/project/${project.projectGuid}/project_page` },
  ]
  if (breadcrumb !== false) {
    breadcrumbSections.push({
      content: breadcrumb || match.params.breadcrumb.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' '),
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
        { as: NavLink, to: sectionConfig.link, activeStyle: { color: '#111', cursor: 'auto' }, exact: true } : {}
      const section =
        <Breadcrumb.Section key={sectionConfig.content} {...sectionProps}>{sectionConfig.content}</Breadcrumb.Section>
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
            <NavLink to={`/project/${project.projectGuid}/case_review`} activeStyle={{ display: 'none' }}>
              <b>Case Review</b><br />
            </NavLink>
        }
        <br />
        {originalPages.map(page =>
          <a
            key={page.name || match.params.breadcrumb}
            href={`/project/${project.deprecatedProjectId}/${match.params.breadcrumbId && page.idPath ? `${page.idPath}/${match.params.breadcrumbId}` : page.path}`}
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


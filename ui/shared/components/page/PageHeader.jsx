import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid, Breadcrumb } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

import { getUser } from 'redux/rootReducer'
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

const BREADCRUMBS = {
  project_page: { breadcrumb: null, originalPages: [{ name: 'Project', path: '' }, { name: 'Families', path: 'families' }] },
  case_review: { breadcrumb: 'Case Review', originalPages: [] },
  saved_variants: { breadcrumb: 'Saved Variants', originalPages: [{ path: 'saved-variants', idPath: 'variants' }] },
}

const PageHeader = ({ user, project, match }) => {
  if (!project || !match) {
    return null
  }
  const { breadcrumb, originalPages } = BREADCRUMBS[match.params.breadcrumb]
  const breadcrumbSections = [
    { content: 'Project' },
    { content: project.name, link: `/project/${project.projectGuid}/project_page` },
  ]
  if (breadcrumb) {
    breadcrumbSections.push({
      content: breadcrumb,
      link: `/project/${project.projectGuid}/${match.params.breadcrumb}`,
    })
  }
  if (match.params.breadcrumbId) {
    breadcrumbSections.push({
      content: match.params.breadcrumbId,
      link: `/project/${project.projectGuid}/${match.params.breadcrumb}/${match.params.breadcrumbId}`,
    })
  }

  const breadcrumbs = breadcrumbSections.reduce(
    (acc, sectionConfig, i, { length }) => {
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
            key={page.name || breadcrumb}
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
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
})

export default connect(mapStateToProps, null, null, { pure: false })(PageHeader)


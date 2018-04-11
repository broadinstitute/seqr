import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'
import { NavLink, Route } from 'react-router-dom'

import { getUser } from 'redux/rootReducer'
import { getProject } from 'pages/Project/reducers'
import EditProjectButton from '../buttons/EditProjectButton'


const PageHeaderRow = styled(Grid.Row)`
  padding: 9px;
  background-color: #F7F7F7;
  max-height: 200px;
  border-bottom: 1px solid #EEEEEE;
`

const ProjectTitleContainer = styled.div`
  font-weight: 300;
  font-size: 36px;
  margin: 50px 0px 35px 0px;
  line-height: 1.2em;
`

const BREADCRUMBS = {
  case_review: 'Case Review',
  saved_variants: 'Saved Variants',
}

const BreadcrumbLink = ({ project, path, text }) =>
  <span> »
    <NavLink
      to={`/project/${project.projectGuid}/${path}`}
      activeStyle={{ color: '#111', fontWeight: 750, cursor: 'auto' }}
      exact
    >
      {text}
    </NavLink>
  </span>

BreadcrumbLink.propTypes = {
  project: PropTypes.object.isRequired,
  path: PropTypes.string.isRequired,
  text: PropTypes.string,
}

const PageHeader = ({ user, project }) => {
  if (!project) {
    return null
  }
  return (
    <PageHeaderRow>
      <Grid.Column width={1} />
      <Grid.Column width={11}>
        <ProjectTitleContainer>
          Project <BreadcrumbLink path="project_page" project={project} text={project.name} />
          <Route
            path="/project/:projectGuid/:breadcrumb/:breadcrumbId?"
            component={({ match }) => {
              const breadcrumb = BREADCRUMBS[match.params.breadcrumb]
              return [
                <DocumentTitle key="title" title={`${breadcrumb || 'seqr'}: ${project.name}`} />,
                breadcrumb ?
                  <BreadcrumbLink key="breadcrumb" path={match.params.breadcrumb} project={project} text={breadcrumb} />
                  : null,
                match.params.breadcrumbId ?
                  <BreadcrumbLink
                    key="breadcrumbId"
                    path={`${match.params.breadcrumb}/${match.params.breadcrumbId}`}
                    project={project}
                    text={match.params.breadcrumbId}
                  /> : null,
              ]
            }}
          />
        </ProjectTitleContainer>
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
        <a href={`/project/${project.deprecatedProjectId}`}>Original Project Page</a><br />
        <a href={`/project/${project.deprecatedProjectId}/families`}>Original Families Page</a><br />
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
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
})

export default connect(mapStateToProps, null, null, { pure: false })(PageHeader)


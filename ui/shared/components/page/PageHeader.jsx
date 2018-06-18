import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'
import { NavLink, Route } from 'react-router-dom'

import { getUser, getProject } from 'redux/rootReducer'
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
  
  a.active {
    color: #111;
    font-weight: 750;
    cursor: auto;
  }
`
const NavLinkNoActive = styled(NavLink)`
  &.active {
    display: none;
  }
`

const BREADCRUMBS = {
  case_review: 'Case Review',
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
          {'Project » '}
          <NavLink to={`/project/${project.projectGuid}/project_page`}>
            {project.name}
          </NavLink>
          <Route
            path="/project/:projectGuid/:breadcrumb"
            component={({ match }) => {
              const breadcrumb = BREADCRUMBS[match.params.breadcrumb]
              return breadcrumb ? <span> » <span style={{ fontWeight: 750 }}>{breadcrumb}</span></span> : null
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
            <NavLinkNoActive to={`/project/${project.projectGuid}/case_review`}>
              <b>Case Review</b><br />
            </NavLinkNoActive>
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


import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'

import { getUser, getProject } from 'redux/rootReducer'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
// TODO shouldn;t hage page specific imports here
import EditProjectButton from 'pages/Project/components/EditProjectButton'


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

const PageHeader = ({ user, project }) => {
  if (!project) {
    return null
  }
  return (
    <PageHeaderRow>
      <Grid.Column width={1} />
      <Grid.Column width={11}>
        <ProjectTitleContainer>
          Project » <span style={{ fontWeight: 750 }}>{project.name}</span>
        </ProjectTitleContainer>
        {
          project.description &&
          <div style={{ fontWeight: 300, fontSize: '16px', margin: '0px 30px 20px 5px', display: 'inline-block' }}>
            {project.description}
          </div>
        }
        <ShowIfEditPermissions><EditProjectButton /></ShowIfEditPermissions>
      </Grid.Column>
      <Grid.Column width={3}>
        <div style={{ margin: '20px 0px 20px 0px' }}>
          {
            project.hasGeneSearch &&
            <b><a href={`/project/${project.deprecatedProjectId}/gene`}><br />Gene Search<br /></a></b>
          }
          {
            user.is_staff &&
            <b><a href={computeCaseReviewUrl(project.projectGuid)}>Case Review<br /><br /></a></b>
          }
          <a href={`/project/${project.deprecatedProjectId}`}>Original Project Page</a><br />
          <a href={`/project/${project.deprecatedProjectId}/families`}>Original Families Page</a><br />
          <br />
          <a href="/gene-lists">Gene Lists</a><br />
          <a href="/gene">Gene Summary Information</a><br />
          {/*<a href={computeVariantSearchUrl(props.project.projectGuid)}>Variant Search</a>*/}
        </div>
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

export default connect(mapStateToProps)(PageHeader)


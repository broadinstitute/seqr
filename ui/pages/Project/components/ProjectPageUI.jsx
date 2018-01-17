import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
import { Table, Form, Grid } from 'semantic-ui-react'
import DocumentTitle from 'react-document-title'

import BaseLayout from 'shared/components/page/BaseLayout'
import { getUser, getProject } from 'shared/utils/redux/commonDataActionsAndSelectors'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'

import EditProjectButton from './EditProjectButton'
import ProjectOverview from './ProjectOverview'
import TableBody from './table-body/TableBody'


const PageHeaderContainer = styled.div`
  margin: 0px 0px 30px 60px;
`

const ProjectTitleContainer = styled.div`
  font-weight: 300;
  font-size: 36px;
  margin: 50px 0px 35px 0px;
  line-height: 1.2em;
`

const ProjectPageUI = props =>
  <BaseLayout pageHeader={
    <PageHeaderContainer>
      <Grid stackable>
        <Grid.Column width={12}>
          <ProjectTitleContainer>
            Project » <span style={{ fontWeight: 750 }}>{props.project.name}</span>
          </ProjectTitleContainer>
          {
            props.project.description &&
            <div style={{ fontWeight: 300, fontSize: '16px', margin: '0px 30px 20px 5px', display: 'inline-block' }}>
              {props.project.description}
            </div>
          }
          <ShowIfEditPermissions><EditProjectButton /></ShowIfEditPermissions>
        </Grid.Column>
        <Grid.Column width={4}>
          <div style={{ margin: '20px 0px 20px 0px' }}>
            {
              props.project.hasGeneSearch &&
              <b><a href={`/project/${props.project.deprecatedProjectId}/gene`}><br />Gene Search<br /></a></b>
            }
            {
              props.user.is_staff &&
              <b><a href={computeCaseReviewUrl(props.project.projectGuid)}>Case Review<br /><br /></a></b>
            }
            <a href={`/project/${props.project.deprecatedProjectId}`}>Original Project Page</a><br />
            <a href={`/project/${props.project.deprecatedProjectId}/families`}>Original Families Page</a><br />

            {/*<a href={computeVariantSearchUrl(props.project.projectGuid)}>Variant Search</a>*/}
          </div>
        </Grid.Column>
      </Grid>
    </PageHeaderContainer>}
  >
    <Form>
      <DocumentTitle title={`seqr: ${props.project.name}`} />
      <ProjectOverview />
      <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
        <ExportTableButton urls={[
          { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_project_families` },
          { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_project_individuals?include_phenotypes=1` }]}
        />
      </div>
      <Table celled style={{ width: '100%' }}>
        <TableBody />
      </Table>
    </Form>

  </BaseLayout>


export { ProjectPageUI as ProjectPageUIComponent }

ProjectPageUI.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
})

export default connect(mapStateToProps)(ProjectPageUI)

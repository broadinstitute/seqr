import React from 'react'
import PropTypes from 'prop-types'

import { Grid, Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
import { InfoBox } from 'shared/components/InfoPanels'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { getUser, getProject } from '../reducers/rootReducer'
//import { getVisibleFamiliesInSortedOrder, getFamilyGuidToIndividuals } from '../utils/visibleFamiliesSelector'

const ProjectOverview = props =>
  <div>
    <div style={{ paddingBottom: '10px' }}>
      <span style={{ fontWeight: 600, fontSize: '18px' }}>{props.project.name}</span>
    </div>
    {props.project.description && <span>{props.project.description}<HorizontalSpacer width={15} /></span>}

    <ShowIfEditPermissions>
      <div><a href={`/project/${props.project.deprecatedProjectId}/edit-basic-info`}>edit</a></div>
    </ShowIfEditPermissions>


    <Grid stackable style={{ margin: '0px' }}>
      <Grid.Column width={8} style={{ paddingLeft: '0' }}>
        <InfoBox leftPadding={0} label={'Variant Tags'} rightOfLabel={<a href={`/project/${props.project.deprecatedProjectId}/saved-variants`}>view all</a>}>
          {
            props.project.variantTagTypes && props.project.variantTagTypes.map((variantTagType, i) => (
              <div key={i}>
                <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', fontWeight: 'bold', paddingRight: '10px' }}>
                  {variantTagType.numTags}
                </span>
                <Icon name="square" size="small" style={{ color: variantTagType.color }} />
                <a href={`/project/${props.project.deprecatedProjectId}/variants/${variantTagType.name}`}>{variantTagType.name}</a>
                {
                  variantTagType.description &&
                  <Popup
                    positioning="right center"
                    trigger={<Icon style={{ color: '#555555', marginLeft: '15px' }} name="help" />}
                    content={variantTagType.description}
                    size="small"
                  />
                }
              </div>),
            )
          }
        </InfoBox>
        <br />
        <InfoBox label={'Pages'}>
          { props.user.is_staff && (<a href={computeCaseReviewUrl(props.project.projectGuid)}>Case Review Page<br /><br /></a>)}

          <a href={`/project/${props.project.deprecatedProjectId}`}>Original Project Page<br /></a>
          <a href={`/project/${props.project.deprecatedProjectId}/families`}>Original Families Page<br /></a>
          <a href={`/project/${props.project.deprecatedProjectId}/individuals`}>Original Individuals Page<br /></a>

          { props.project.hasGeneSearch && <a href={`/project/${props.project.deprecatedProjectId}/gene`}><br />Gene Search<br /><br /></a>}
        </InfoBox>

      </Grid.Column>

      <Grid.Column width={8} style={{ paddingLeft: '0' }}>
        <InfoBox
          label="Collaborators"
          rightOfLabel={
            <ShowIfEditPermissions>
              <a href={`/project/${props.project.deprecatedProjectId}/collaborators`}>edit</a>
            </ShowIfEditPermissions>}
        >
          {
            props.project.collaborators.map((collaborator, i) => <div key={i}>
              {
                collaborator.email ?
                  <a href={`mailto:${collaborator.email}`}>{collaborator.displayName || collaborator.email}</a> :
                  (collaborator.displayName || collaborator.username)
              }
              <Popup
                positioning="top center"
                trigger={<b> {collaborator.hasEditPermissions ? '†' : ' '}</b>}
                content={'Has Edit permissions'}
                size="small"
              />
            </div>)
          }
        </InfoBox>
        <InfoBox
          label="Gene Lists"
          rightOfLabel={
            <ShowIfEditPermissions>
              <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>edit</a>
            </ShowIfEditPermissions>
          }
        >
          {
            props.project.geneLists.map((geneList, i) => (
              <div key={i}><b>{geneList.name}</b>
                <span style={{ paddingLeft: '10px' }}>
                  (<i>
                    <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
                      {`${geneList.numEntries} entries`}
                    </a>
                  </i>)
                </span>
                <span style={{ color: 'gray' }}><br />{geneList.description}</span>
              </div>),
            )
          }
        </InfoBox>
      </Grid.Column>
    </Grid>

    <h3>Families:</h3>
  </div>

export { ProjectOverview as ProjectOverviewComponent }

ProjectOverview.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  //sampleBatchesByGuid: PropTypes.object,
  //samplesByGuid: PropTypes.object,
  //visibleFamilies: PropTypes.array.isRequired,
  //familyGuidToIndividuals: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
  //sampleBatchesByGuid: getSampleBatchesByGuid(state),
  //samplesByGuid: getSamplesByGuid(state),
  //visibleFamilies: getVisibleFamiliesInSortedOrder(state),
  //familyGuidToIndividuals: getFamilyGuidToIndividuals(state),
})

export default connect(mapStateToProps)(ProjectOverview)

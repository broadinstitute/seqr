import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'

import { Grid, Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
import { InfoBox } from 'shared/components/InfoPanels'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import ShowEditFamiliesAndIndividualsModalButton from 'shared/components/panel/edit-families-and-individuals/ShowEditFamiliesAndIndividualsModalButton'
import { HorizontalSpacer } from 'shared/components/Spacers'
import EditProjectButton from './EditProjectButton'
import { getUser, getProject } from '../reducers/rootReducer'

//import { getVisibleFamiliesInSortedOrder, getFamilyGuidToIndividuals } from '../utils/visibleFamiliesSelector'

const ProjectOverview = props =>
  <div>
    <div style={{ paddingBottom: '10px' }}>
      <span style={{ fontWeight: 600, fontSize: '18px' }}>{props.project.name}</span>
    </div>
    {props.project.description && <span>{props.project.description}<HorizontalSpacer width={15} /></span>}
    <ShowIfEditPermissions><EditProjectButton /></ShowIfEditPermissions>

    <Grid stackable style={{ margin: '0px' }}>
      <Grid.Column width={4} style={{ paddingLeft: '0' }}>
        <InfoBox leftPadding={0} label={'Variant Tags'} rightOfLabel={<a href={`/project/${props.project.deprecatedProjectId}/saved-variants`}>view all</a>}>
          {
            props.project.variantTagTypes && props.project.variantTagTypes.map((variantTagType, i) => (
              <div key={i} style={{ whitespace: 'nowrap' }}>
                <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', fontWeight: 'bold', paddingRight: '10px' }}>
                  {variantTagType.numTags}
                </span>
                <Icon name="square" size="small" style={{ color: variantTagType.color }} />
                <a href={`/project/${props.project.deprecatedProjectId}/variants/${variantTagType.name}`}>{variantTagType.name}</a>
                {
                  variantTagType.description &&
                  <Popup
                    positioning="top center"
                    trigger={<Icon style={{ cursor: 'pointer', color: '#555555', marginLeft: '15px' }} name="help circle outline" />}
                    content={variantTagType.description}
                    size="small"
                  />
                }
              </div>),
            )
          }
        </InfoBox>
      </Grid.Column>

      <Grid.Column width={4} style={{ paddingLeft: '0' }}>
        <InfoBox
          label="Gene Lists"
          rightOfLabel={
            <ShowIfEditPermissions>
              <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
                <Icon link size="small" name="write" />
              </a>
            </ShowIfEditPermissions>
          }
        >
          {
            props.project.geneLists.map((geneList, i) => (
              <div key={i} style={{ whitespace: 'nowrap' }}>
                {geneList.name}
                <span style={{ paddingLeft: '10px' }}>
                  (<i>
                    <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
                      {`${geneList.numEntries} entries`}
                    </a>
                  </i>)
                </span>
                {
                  geneList.description &&
                  <Popup
                    positioning="right center"
                    trigger={<Icon style={{ cursor: 'pointer', color: '#555555', marginLeft: '10px' }} name="help circle outline" />}
                    content={geneList.description}
                    size="small"
                  />
                }
              </div>),
            )
          }
        </InfoBox>
      </Grid.Column>
      <Grid.Column width={5} style={{ paddingLeft: '0' }}>
        <InfoBox
          label="Collaborators"
          leftPadding={0}
          rightOfLabel={
            <ShowIfEditPermissions>
              <a href={`/project/${props.project.deprecatedProjectId}/collaborators`}><Icon link size="small" name="write" /></a>
            </ShowIfEditPermissions>}
        >
          <table>
            <tbody>
              {
                orderBy(props.project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
                  <tr key={i}>
                    <td style={{ padding: '1px 10px', textAlign: 'center' }}>
                      <Popup
                        positioning="top center"
                        trigger={<b style={{ cursor: 'pointer' }}> {c.hasEditPermissions ? ' † ' : ' '}</b>}
                        content={"Has 'edit' permissions"}
                        size="small"
                      />
                    </td>
                    <td style={{ padding: '1px 5px' }}>
                      {c.displayName ? `${c.displayName} ▪ ` : null}
                      {
                        c.email ?
                          <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
                      }

                    </td>
                  </tr>,
                )
              }
            </tbody>
          </table>
        </InfoBox>
      </Grid.Column>
      <Grid.Column width={3} style={{ paddingLeft: '0' }}>
        <InfoBox label={'Pages'}>
          <b>
            { props.project.hasGeneSearch && <a href={`/project/${props.project.deprecatedProjectId}/gene`}><br />Gene Search<br /></a>}
            { props.user.is_staff && (<a href={computeCaseReviewUrl(props.project.projectGuid)}>Case Review<br /><br /></a>)}
          </b>

          <a href={`/project/${props.project.deprecatedProjectId}`}>Original Project Page<br /></a>
          <a href={`/project/${props.project.deprecatedProjectId}/families`}>Original Families Page<br /></a>
          <a href={`/project/${props.project.deprecatedProjectId}/individuals`}>Original Individuals Page<br /></a>

          <ShowIfEditPermissions>
            <span><br /><ShowEditFamiliesAndIndividualsModalButton /></span>
          </ShowIfEditPermissions>
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

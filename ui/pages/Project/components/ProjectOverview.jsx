/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'

import { Table, Grid, Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
import { InfoBox } from 'shared/components/InfoPanels'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import ShowAddOrEditIndividualsModalButton from 'shared/components/panel/add-or-edit-individuals/ShowAddOrEditIndividualsModalButton'
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
        <InfoBox leftPadding={0} label="Variant Tags" rightOfLabel={<a href={`/project/${props.project.deprecatedProjectId}/saved-variants`}>view all</a>}>
          {
            props.project.variantTagTypes && props.project.variantTagTypes.map(variantTagType => (
              <div key={variantTagType.variantTagTypeGuid} style={{ whitespace: 'nowrap' }}>
                <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', fontWeight: 'bold', paddingRight: '10px' }}>
                  {variantTagType.numTags}
                </span>
                <Icon name="square" size="small" style={{ color: variantTagType.color }} />
                <a href={`/project/${props.project.deprecatedProjectId}/variants/${variantTagType.name}`}>{variantTagType.name}</a>
                {
                  variantTagType.description &&
                  <Popup
                    position="right center"
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

      <Grid.Column width={5} style={{ paddingLeft: '0' }}>
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
            props.project.locusLists && props.project.locusLists.map(locusList => (
              <div key={locusList.locusListGuid} style={{ padding: '2px 0px', whitespace: 'nowrap' }}>
                {locusList.name}
                <span style={{ paddingLeft: '10px' }}>
                  <i>
                    <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
                      {`${locusList.numEntries} entries`}
                    </a>
                  </i>
                </span>
                {
                  locusList.description &&
                  <Popup
                    position="right center"
                    trigger={<Icon style={{ cursor: 'pointer', color: '#555555', marginLeft: '10px' }} name="help circle outline" />}
                    content={locusList.description}
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
          <Table className="noBorder">
            <Table.Body className="noBorder">
              {
                orderBy(props.project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
                  <Table.Row key={i} className="noBorder">
                    <Table.Cell style={{ padding: '2px 10px', textAlign: 'center', verticalAlign: 'top' }} className="noBorder">
                      <Popup
                        position="top center"
                        trigger={<b style={{ cursor: 'pointer' }}> {c.hasEditPermissions ? ' † ' : ' '}</b>}
                        content={"Has 'edit' permissions"}
                        size="small"
                      />
                    </Table.Cell>
                    <Table.Cell style={{ padding: '2px 5px' }} className="noBorder">
                      {c.displayName ? `${c.displayName} ▪ ` : null}
                      {
                         c.email ?
                           <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
                      }

                    </Table.Cell>
                  </Table.Row>,
                )
              }
            </Table.Body>
          </Table>
        </InfoBox>
      </Grid.Column>
      <Grid.Column width={2} style={{ paddingLeft: '0' }}>
        <Table className="noBorder">
          <Table.Body className="noBorder">
            {
              props.project.hasGeneSearch &&
              <Table.Row className="noBorder">
                <Table.Cell className="noBorder" style={{ padding: '0px 0px 5px 10px' }}>
                  <b><a href={`/project/${props.project.deprecatedProjectId}/gene`}><br />Gene Search<br /></a></b>
                </Table.Cell>
              </Table.Row>
            }
            {
              props.user.is_staff &&
              <Table.Row className="noBorder">
                <Table.Cell className="noBorder" style={{ padding: '0px 0px 5px 10px' }}>
                  <b><a href={computeCaseReviewUrl(props.project.projectGuid)}>Case Review<br /><br /></a></b>
                </Table.Cell>
              </Table.Row>
            }
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={{ padding: '0px 0px 5px 10px' }}>
                <a href={`/project/${props.project.deprecatedProjectId}`}>Original Project Page<br /></a>
              </Table.Cell>
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={{ padding: '0px 0px 5px 10px' }}>
                <a href={`/project/${props.project.deprecatedProjectId}/families`}>Original Families Page<br /></a>
              </Table.Cell>
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={{ padding: '0px 0px 5px 10px' }}>
                <a href={`/project/${props.project.deprecatedProjectId}/individuals`}>Original Indiv. Page<br /></a>
              </Table.Cell>
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={{ padding: '0px 0px 5px 10px' }}>
                <ShowIfEditPermissions><span><br /><ShowAddOrEditIndividualsModalButton /></span></ShowIfEditPermissions>
              </Table.Cell>
            </Table.Row>

          </Table.Body>
        </Table>
      </Grid.Column>
    </Grid>

    <h3>Families:</h3>
  </div>

export { ProjectOverview as ProjectOverviewComponent }

ProjectOverview.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  //datasetsByGuid: PropTypes.object,
  //samplesByGuid: PropTypes.object,
  //visibleFamilies: PropTypes.array.isRequired,
  //familyGuidToIndividuals: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getProject(state),
  //datasetsByGuid: getDatasetsByGuid(state),
  //samplesByGuid: getSamplesByGuid(state),
  //visibleFamilies: getVisibleFamiliesInSortedOrder(state),
  //familyGuidToIndividuals: getFamilyGuidToIndividuals(state),
})

export default connect(mapStateToProps)(ProjectOverview)

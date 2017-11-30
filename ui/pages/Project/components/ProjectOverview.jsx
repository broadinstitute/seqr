/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import orderBy from 'lodash/orderBy'
import styled from 'styled-components'

import { Table, Grid, Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { VerticalSpacer } from 'shared/components/Spacers'
import { getProject, getFamiliesByGuid, getIndividualsByGuid } from 'shared/utils/commonSelectors'

import { getFamilySizeHistogram, getHpoTermHistogram } from '../utils/histogramSelectors'


//import { getVisibleFamiliesInSortedOrder, getFamilyGuidToIndividuals } from '../utils/visibleFamiliesSelector'
const SectionHeader = styled.div`
  padding-top: 8px;
  padding-bottom: 6px;
  margin: 8px 0 15px 0;
  border-bottom: 1px solid #EEE;
  font-family: 'Lato';
  font-weight: 300;
  font-size: 18px; 
`

/*
Add charts:
- number of individuals per family
- analysis status

Phenotypes:
- how many families have phenotype terms in each category

Data loaded:
- datasets - readviz, etc

- what's new
 */

const FAMILY_SIZE_LABELS = {
  1: ' families with 1 individual',
  2: ' families with 2 individuals',
  3: ' trios',
  4: ' quads',
  5: ' families with 5+ individuals',
}

const ProjectOverview = props => (
  <div>
    <Grid stackable style={{ margin: '0px', padding: '0px' }}>
      <Grid.Column width={4} style={{ margin: '0px', padding: '0px' }}>
        <SectionHeader>
          Overview
        </SectionHeader>
        <Grid>
          <Grid.Column>
            <div>
              {Object.keys(props.familiesByGuid).length} Families, {Object.keys(props.individualsByGuid).length} Individuals
            </div>
            <div style={{ padding: '5px 0px 0px 20px' }}>
              {
                sortBy(Object.keys(props.familySizeHistogram)).map(size =>
                  <div key={size}>
                    {props.familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size]}
                  </div>)
              }
            </div>
            {console.log('hpoTerms', props.hpoTermHistogram)}
          </Grid.Column>
        </Grid>
      </Grid.Column>
      <Grid.Column width={12} />
    </Grid>
    <Grid stackable style={{ margin: '0px' }}>
      <Grid.Column width={12} style={{ paddingLeft: '0' }}>
        <SectionHeader>
          Variant Tags
        </SectionHeader>
        <div style={{ display: 'block', padding: '0px 0px 10px 0px' }}>
          {
            props.project.variantTagTypes && props.project.variantTagTypes.map(variantTagType => (
              <div key={variantTagType.variantTagTypeGuid} style={{ whitespace: 'nowrap' }}>
                {
                  <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', paddingRight: '10px' }}>
                    {variantTagType.numTags > 0 && <span style={{ fontWeight: 'bold' }}>{variantTagType.numTags}</span>}
                  </span>
                }
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
        </div>
        <div style={{ paddingTop: '15px', paddingLeft: '35px' }}>
          <a href={`/project/${props.project.deprecatedProjectId}/saved-variants`}>View All</a>
        </div>

      </Grid.Column>

      <Grid.Column width={4} style={{ paddingLeft: '0' }}>
        <SectionHeader>Collaborators</SectionHeader>
        <Table className="noBorder">
          <Table.Body className="noBorder">
            {
              orderBy(props.project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
                <Table.Row key={i} className="noBorder">
                  <Table.Cell style={{ padding: '0px' }} className="noBorder">
                    {c.displayName ? `${c.displayName} ▪ ` : null}
                    {
                       c.email ?
                         <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
                    }

                  </Table.Cell>
                  <Table.Cell style={{ padding: '2px 10px', textAlign: 'center', verticalAlign: 'top' }} className="noBorder">
                    <Popup
                      position="top center"
                      trigger={<b style={{ cursor: 'pointer' }}> {c.hasEditPermissions ? ' † ' : ' '}</b>}
                      content={"Has 'Manager' permissions"}
                      size="small"
                    />
                  </Table.Cell>
                </Table.Row>,
              )
            }
          </Table.Body>
        </Table>
        <ShowIfEditPermissions>
          <a href={`/project/${props.project.deprecatedProjectId}/collaborators`}>
            Edit Collaborators
          </a>
        </ShowIfEditPermissions>
        <VerticalSpacer height={30} />
        <SectionHeader>
          Gene Lists
        </SectionHeader>
        <div style={{ marginBottom: '14px' }}>
          {
            props.project.locusLists &&
            props.project.locusLists.map(locusList => (
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
        </div>
        <ShowIfEditPermissions>
          <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
            Edit Gene Lists
          </a>
        </ShowIfEditPermissions>
      </Grid.Column>
    </Grid>

    {/* TODO add histograms, what's new, analysis status distribution */}
    <SectionHeader>Families</SectionHeader>
  </div>)


ProjectOverview.propTypes = {
  project: PropTypes.object.isRequired,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  familySizeHistogram: PropTypes.object.isRequired,
  hpoTermHistogram: PropTypes.object.isRequired,
  //datasetsByGuid: PropTypes.object,
  //samplesByGuid: PropTypes.object,
  //visibleFamilies: PropTypes.array.isRequired,
  //familyGuidToIndividuals: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
  familySizeHistogram: getFamilySizeHistogram(state),
  hpoTermHistogram: getHpoTermHistogram(state),
  //datasetsByGuid: getDatasetsByGuid(state),
  //samplesByGuid: getSamplesByGuid(state),
  //visibleFamilies: getVisibleFamiliesInSortedOrder(state),
  //familyGuidToIndividuals: getFamilyGuidToIndividuals(state),
})


export { ProjectOverview as ProjectOverviewComponent }

export default connect(mapStateToProps)(ProjectOverview)

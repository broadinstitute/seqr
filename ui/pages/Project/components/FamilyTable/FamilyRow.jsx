import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Icon, Popup } from 'semantic-ui-react'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import ListFieldView from 'shared/components/panel/view-fields/ListFieldView'
import { FAMILY_ANALYSIS_STATUS_LOOKUP } from 'shared/constants/familyAndIndividualConstants'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { updateFamilies } from 'redux/rootReducer'

import { getShowDetails, getProject } from '../../reducers'


const FamilyRow = (props) => {
  const familyAnalysisStatus = (
    (props.family.analysisStatus && FAMILY_ANALYSIS_STATUS_LOOKUP[props.family.analysisStatus]) ?
      FAMILY_ANALYSIS_STATUS_LOOKUP[props.family.analysisStatus] :
      {}
  )

  const familyRow = (
    <Grid stackable style={{ width: '100%' }}>
      <Grid.Row style={{ paddingTop: '20px', paddingRight: '10px' }}>
        <Grid.Column width={3} style={{ maxWidth: '250px' }}>
          <span style={{ paddingLeft: '0px' }}>
            <b>
              Family: &nbsp;
              <a href={`/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}`}>
                {props.family.displayName}
              </a>
            </b>
            {/*
              (props.family.causalInheritanceMode && props.family.causalInheritanceMode !== 'unknown') ?
              `Inheritance: ${props.family.causalInheritanceMode}` :
              null
             http://localhost:3000/project/pierce_retinal-degeneration_cmg-samples_genomes-and-arrays_v1/family/OGI001/edit
            */}
            <br />
          </span>
          <br />
          <PedigreeImagePanel family={props.family} />
        </Grid.Column>

        <Grid.Column width={10} style={{ maxWidth: '950px' }}>
          <TextFieldView
            isVisible={props.showDetails}
            isEditable={props.project.canEdit && !props.showInternalFields}
            fieldName="Family Description"
            fieldId="description"
            initialText={props.family.description}
            textEditorId={`editDescriptions-${props.family.familyGuid}`}
            textEditorTitle={`Description for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
          />
          {!props.showInternalFields &&
            <div style={{ whiteSpace: 'nowrap' }}>
              <div style={{ display: 'inline-block', padding: '5px 15px 5px 0px' }}><b>Analysis Status: </b></div>
              <Popup
                trigger={<Icon name="play" style={{ color: familyAnalysisStatus.color }} />}
                content={<div>Analysis Status:<br />{familyAnalysisStatus.name}</div>}
              />
              {familyAnalysisStatus.name}
              <ShowIfEditPermissions>
                <a
                  style={{ paddingLeft: '15px' }}
                  href={`/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}/edit`}
                >
                  <Icon name="write" size="small" />
                </a>
              </ShowIfEditPermissions>
            </div>
          }
          <ListFieldView
            isVisible={props.showDetails}
            isEditable={props.project.canEdit && !props.showInternalFields}
            fieldName="Analysed By"
            values={props.family.analysedBy.map(analysedBy => `${analysedBy.user.display_name} (${analysedBy.date_saved})`)}
            addItemUrl={`/api/family/${props.family.familyGuid}/update_analysed_by`}
            onItemAdded={props.updateFamily}
            confirmAddMessage="Are you sure you want to add that you analysed this family?"
          />
          <TextFieldView
            isVisible={props.showDetails}
            isEditable={props.project.canEdit && !props.showInternalFields}
            fieldName="Analysis Notes"
            fieldId="analysisNotes"
            initialText={props.family.analysisNotes}
            textEditorId={`editAnalysisNotes-${props.family.familyGuid}`}
            textEditorTitle={`Analysis Notes for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
          />
          <TextFieldView
            isVisible={props.showDetails}
            isEditable={props.project.canEdit && !props.showInternalFields}
            fieldName="Analysis Summary"
            fieldId="analysisSummary"
            initialText={props.family.analysisSummary}
            textEditorId={`editAnalysisSummary-${props.family.familyGuid}`}
            textEditorTitle={`Analysis Summary for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
          />
          <TextFieldView
            isPrivate
            isVisible={props.showInternalFields || false}
            isEditable={props.project.canEdit}
            fieldName="Internal Notes"
            fieldId="internalCaseReviewNotes"
            initialText={props.family.internalCaseReviewNotes}
            textEditorId={`editInternalNotes-${props.family.familyGuid}`}
            textEditorTitle={`Internal Notes for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
          />
          <TextFieldView
            isPrivate
            isVisible={props.showInternalFields || false}
            isEditable={props.project.canEdit}
            fieldName="Internal Summary"
            fieldId="internalCaseReviewSummary"
            initialText={props.family.internalCaseReviewSummary}
            textEditorId={`editInternalSummary-${props.family.familyGuid}`}
            textEditorTitle={`Internal Summary for Family ${props.family.displayName}`}
            textEditorSubmit={props.updateFamily}
          />
          <br />
        </Grid.Column>
        {!props.showInternalFields &&
          <Grid.Column width={3}>
            <a
              style={{ display: 'block', padding: '5px 0px' }}
              href={`/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}`}
            >
              Family Page
            </a>
            <a
              style={{ display: 'block', padding: '5px 0px' }}
              href={`/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}/mendelian-variant-search`}
            >
              <Icon name="search" />Variant Search
            </a>
            {/*
            <a style={{ display: 'block', padding: '5px 0px' }}
              href={computeVariantSearchUrl(props.project.projectGuid, props.family.familyGuid)}
            >
              <Icon name="search" />Variant Search
            </a>
            */}
            {
              props.project.isMmeEnabled &&
              <a
                style={{ display: 'block', padding: '5px 0px' }}
                href={`/matchmaker/search/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}`}
              >
                <Icon name="search" />Match Maker Exchange
              </a>
            }
          </Grid.Column>
        }
      </Grid.Row>
    </Grid>)

  return familyRow
}

export { FamilyRow as FamilyRowComponent }

FamilyRow.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  showDetails: PropTypes.bool.isRequired,
  showInternalFields: PropTypes.bool,
}


const mapStateToProps = state => ({
  project: getProject(state),
  showDetails: getShowDetails(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateFamily: (values) => {
      dispatch(updateFamilies({ families: [{ familyGuid: ownProps.family.familyGuid, ...values }] }))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(FamilyRow)

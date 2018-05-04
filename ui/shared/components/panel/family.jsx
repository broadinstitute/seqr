import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Icon, Header } from 'semantic-ui-react'

import { updateFamily, getProjectsByGuid } from 'redux/rootReducer'
import VariantTagTypeBar from '../graph/VariantTagTypeBar'
import PedigreeImagePanel from './view-pedigree-image/PedigreeImagePanel'
import OptionFieldView from './view-fields/OptionFieldView'
import TextFieldView from './view-fields/TextFieldView'
import ListFieldView from './view-fields/ListFieldView'
import { VerticalSpacer } from '../Spacers'
import { FAMILY_ANALYSIS_STATUS_OPTIONS } from '../../utils/constants'


const Family = ({ project, family, showDetails, showInternalFields, canEdit, useFullWidth, updateFamily: dispatchUpdateFamily }) =>
  <Grid stackable style={{ width: '100%' }}>
    <Grid.Row style={{ paddingTop: '20px', paddingRight: '10px' }}>
      <Grid.Column width={(useFullWidth && showInternalFields) ? 5 : 3} style={{ maxWidth: '250px' }}>
        <Header size="small">
          Family: {family.displayName}
        </Header>
        <PedigreeImagePanel family={family} />
      </Grid.Column>

      <Grid.Column width={(useFullWidth && showInternalFields) ? 11 : 10} style={{ maxWidth: '950px' }}>
        <TextFieldView
          isVisible={showDetails}
          isEditable={canEdit && project.canEdit && !showInternalFields}
          fieldName="Family Description"
          fieldId="description"
          initialValues={family}
          textEditorId={`editDescriptions-${family.familyGuid}`}
          textEditorTitle={`Description for Family ${family.displayName}`}
          textEditorSubmit={dispatchUpdateFamily}
        />
        <OptionFieldView
          isEditable={canEdit && project.canEdit && !showInternalFields}
          fieldName="Analysis Status"
          field="analysisStatus"
          idField="familyGuid"
          initialValues={family}
          modalTitle={`Anlysis Status for Family ${family.displayName}`}
          onSubmit={dispatchUpdateFamily}
          tagOptions={FAMILY_ANALYSIS_STATUS_OPTIONS}
          tagAnnotation={value => <Icon name="play" style={{ color: value.color }} />}
        />
        <ListFieldView
          isVisible={showDetails}
          isEditable={canEdit && project.canEdit && !showInternalFields}
          fieldName="Analysed By"
          fieldId="analysedBy"
          initialValues={family}
          formatValue={analysedBy => `${analysedBy.user.display_name} (${analysedBy.date_saved})`}
          onSubmit={values => dispatchUpdateFamily({ ...values, familyField: 'analysed_by' })}
          addConfirm="Are you sure you want to add that you analysed this family?"
        />
        <TextFieldView
          isVisible={showDetails}
          isEditable={canEdit && project.canEdit && !showInternalFields}
          fieldName="Analysis Notes"
          fieldId="analysisNotes"
          initialValues={family}
          textEditorId={`editAnalysisNotes-${family.familyGuid}`}
          textEditorTitle={`Analysis Notes for Family ${family.displayName}`}
          textEditorSubmit={dispatchUpdateFamily}
        />
        <TextFieldView
          isVisible={showDetails}
          isEditable={canEdit && project.canEdit && !showInternalFields}
          fieldName="Analysis Summary"
          fieldId="analysisSummary"
          initialValues={family}
          textEditorId={`editAnalysisSummary-${family.familyGuid}`}
          textEditorTitle={`Analysis Summary for Family ${family.displayName}`}
          textEditorSubmit={dispatchUpdateFamily}
        />
        <TextFieldView
          isPrivate
          isVisible={showInternalFields || false}
          isEditable={canEdit && project.canEdit}
          fieldName="Internal Notes"
          fieldId="internalCaseReviewNotes"
          initialValues={family}
          textEditorId={`editInternalNotes-${family.familyGuid}`}
          textEditorTitle={`Internal Notes for Family ${family.displayName}`}
          textEditorSubmit={dispatchUpdateFamily}
        />
        <TextFieldView
          isPrivate
          isVisible={showInternalFields || false}
          isEditable={canEdit && project.canEdit}
          fieldName="Internal Summary"
          fieldId="internalCaseReviewSummary"
          initialValues={family}
          textEditorId={`editInternalSummary-${family.familyGuid}`}
          textEditorTitle={`Internal Summary for Family ${family.displayName}`}
          textEditorSubmit={dispatchUpdateFamily}
        />
        <br />
      </Grid.Column>
      {!showInternalFields &&
        <Grid.Column width={3}>
          <VariantTagTypeBar height={15} project={project} familyGuid={family.familyGuid} />
          <VerticalSpacer height={20} />
          <a
            style={{ display: 'block', padding: '5px 0px' }}
            href={`/project/${project.deprecatedProjectId}/family/${family.familyId}`}
          >
            Original Family Page
          </a>
          <a
            style={{ display: 'block', padding: '5px 0px' }}
            href={`/project/${project.deprecatedProjectId}/family/${family.familyId}/mendelian-variant-search`}
          >
            <Icon name="search" />Variant Search
          </a>
          {
            project.isMmeEnabled &&
            <a
              style={{ display: 'block', padding: '5px 0px' }}
              href={`/matchmaker/search/project/${project.deprecatedProjectId}/family/${family.familyId}`}
            >
              <Icon name="search" />Match Maker Exchange
            </a>
          }
        </Grid.Column>
      }
    </Grid.Row>
  </Grid>

export { Family as FamilyComponent }

Family.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  canEdit: PropTypes.bool,
  showDetails: PropTypes.bool,
  showInternalFields: PropTypes.bool,
  useFullWidth: PropTypes.bool,
  updateFamily: PropTypes.func,
}


const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = {
  updateFamily,
}

export default connect(mapStateToProps, mapDispatchToProps)(Family)

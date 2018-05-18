import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Icon, Header } from 'semantic-ui-react'

import { updateFamily } from 'redux/rootReducer'
import { getProjectsByGuid } from 'redux/selectors'
import VariantTagTypeBar from '../graph/VariantTagTypeBar'
import { ColoredIcon } from '../StyledComponents'
import PedigreeImagePanel from './view-pedigree-image/PedigreeImagePanel'
import OptionFieldView from './view-fields/OptionFieldView'
import TextFieldView from './view-fields/TextFieldView'
import ListFieldView from './view-fields/ListFieldView'
import { VerticalSpacer } from '../Spacers'
import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_ANALYSIS_STATUS_OPTIONS,
} from '../../utils/constants'


const fieldRenderDetails = {
  [FAMILY_FIELD_DESCRIPTION]: { name: 'Family Description' },
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    name: 'Analysis Status',
    component: OptionFieldView,
    props: {
      tagOptions: FAMILY_ANALYSIS_STATUS_OPTIONS,
      tagAnnotation: value => <ColoredIcon name="play" color={value.color} />,
    },
  },
  [FAMILY_FIELD_ANALYSED_BY]: {
    name: 'Analysed By',
    component: ListFieldView,
    submitArgs: { familyField: 'analysed_by' },
    props: {
      addConfirm: 'Are you sure you want to add that you analysed this family?',
      formatValue: analysedBy => `${analysedBy.user.display_name} (${analysedBy.date_saved})`,
    },
  },
  [FAMILY_FIELD_ANALYSIS_NOTES]: { name: 'Analysis Notes' },
  [FAMILY_FIELD_ANALYSIS_SUMMARY]: { name: 'Analysis Summary' },
  [FAMILY_FIELD_INTERNAL_NOTES]: { name: 'Internal Notes', internal: true },
  [FAMILY_FIELD_INTERNAL_SUMMARY]: { name: 'Internal Summary', internal: true },
}


const Family = ({ project, family, fields = [], showSearchLinks, useFullWidth, disablePedigreeZoom, updateFamily: dispatchUpdateFamily }) =>
  <Grid stackable>
    <Grid.Row>
      <Grid.Column width={(useFullWidth && !showSearchLinks) ? 6 : 3}>
        <Header size="small">
          Family: {family.displayName}
        </Header>
        <PedigreeImagePanel family={family} disablePedigreeZoom={disablePedigreeZoom} />
      </Grid.Column>

      <Grid.Column width={10}>
        {fields.map((field) => {
          const renderDetails = fieldRenderDetails[field.id]
          const submitFunc = renderDetails.submitArgs ?
            values => dispatchUpdateFamily({ ...values, ...renderDetails.submitArgs }) : dispatchUpdateFamily
          return React.createElement(renderDetails.component || TextFieldView, {
            key: field.id,
            isEditable: project.canEdit && field.canEdit,
            isPrivate: renderDetails.internal,
            fieldName: renderDetails.name,
            field: field.id,
            idField: 'familyGuid',
            initialValues: family,
            onSubmit: submitFunc,
            modalTitle: `${renderDetails.name} for Family ${family.displayName}`,
            ...(renderDetails.props || {}),
          }) },
        )}
      </Grid.Column>
      {showSearchLinks &&
        <Grid.Column width={3}>
          <VariantTagTypeBar height={15} project={project} familyGuid={family.familyGuid} />
          <VerticalSpacer height={20} />
          <a href={`/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
            Original Family Page
          </a>
          <VerticalSpacer height={10} />
          <a href={`/project/${project.deprecatedProjectId}/family/${family.familyId}/mendelian-variant-search`}>
            <Icon name="search" />Variant Search
          </a>
          <VerticalSpacer height={10} />
          {
            project.isMmeEnabled &&
            <a href={`/matchmaker/search/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
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
  fields: PropTypes.array,
  showSearchLinks: PropTypes.bool,
  useFullWidth: PropTypes.bool,
  disablePedigreeZoom: PropTypes.bool,
  updateFamily: PropTypes.func,
}


const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = {
  updateFamily,
}

export default connect(mapStateToProps, mapDispatchToProps)(Family)

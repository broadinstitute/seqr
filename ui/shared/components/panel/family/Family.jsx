import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { updateFamily } from 'redux/rootReducer'
import { getProjectsByGuid } from 'redux/selectors'

import PedigreeImagePanel from '../view-pedigree-image/PedigreeImagePanel'
import TextFieldView from '../view-fields/TextFieldView'
import { InlineHeader } from '../../StyledComponents'
import {
  FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ASSIGNED_ANALYST,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_SUCCESS_STORY_TYPE_OPTIONS,
  successStoryTypeDisplay,
  FAMILY_FIELD_SUCCESS_STORY_TYPE,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_RENDER_LOOKUP,
  FAMILY_FIELD_OMIM_NUMBER,
  FAMILY_FIELD_PMIDS,
} from '../../../utils/constants'
import { FirstSample, AnalystEmailDropdown, AnalysedBy, analysisStatusIcon } from './FamilyFields'
import FamilyLayout from './FamilyLayout'


const EDIT_FIELDS = [
  {
    name: 'assigned_analyst_username',
    label: 'Email',
    component: AnalystEmailDropdown,
    width: 16,
    inline: true,
  },
]


const familyFieldRenderProps = {
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    tagOptions: FAMILY_ANALYSIS_STATUS_OPTIONS,
    tagAnnotation: analysisStatusIcon,
  },
  [FAMILY_FIELD_ASSIGNED_ANALYST]: {
    formFields: EDIT_FIELDS,
    addConfirm: 'Are you sure you want to add the analyst to this family?',
    fieldDisplay: value => (value ? <div>{(value.fullName) ? value.fullName : value.email}</div> :
      ''),
  },
  [FAMILY_FIELD_ANALYSED_BY]: {
    addConfirm: 'Are you sure you want to add that you analysed this family?',
    fieldDisplay: (analysedByList, compact) => <AnalysedBy analysedByList={analysedByList} compact={compact} />,
  },
  [FAMILY_FIELD_SUCCESS_STORY_TYPE]: {
    tagOptions: FAMILY_SUCCESS_STORY_TYPE_OPTIONS,
    simplifiedValue: true,
    fieldDisplay: value => value.map(tag => <div key={tag}>{successStoryTypeDisplay(tag)}</div>,
    ),
  },
  [FAMILY_FIELD_FIRST_SAMPLE]: {
    showEmptyValues: true,
    fieldDisplay: (loadedSample, compact, familyGuid) =>
      <FirstSample familyGuid={familyGuid} compact={compact} />,
  },
  [FAMILY_FIELD_OMIM_NUMBER]: {
    fieldDisplay: value => <a target="_blank" href={`https://www.omim.org/entry/${value}`}>{value}</a>,
  },
  [FAMILY_FIELD_PMIDS]: {
    itemDisplay: value => <a target="_blank" href={`https://www.ncbi.nlm.nih.gov/pubmed/${value}`}>{value}</a>,
    addElementLabel: 'Add publication',
    addConfirm: 'This field is intended for publications which list this gene discovery on this particular family only. It is not intended for gene or phenotype level evidence, which should be added to the notes field.',
  },
}


const Family = React.memo((
  { project, family, fields = [], rightContent, compact, useFullWidth, disablePedigreeZoom, disableEdit,
    showFamilyPageLink, annotation, updateFamily: dispatchUpdateFamily, hidePedigree, disableInternalEdit,
  }) => {
  if (!family) {
    return <div>Family Not Found</div>
  }

  const familyField = (field) => {
    const { submitArgs, component, canEdit, internal, name } = FAMILY_FIELD_RENDER_LOOKUP[field.id]
    const submitFunc = submitArgs ?
      values => dispatchUpdateFamily({ ...values, ...submitArgs }) : dispatchUpdateFamily
    return React.createElement(component || TextFieldView, {
      key: field.id,
      isEditable: !disableEdit && (canEdit || (!disableInternalEdit && internal)),
      isPrivate: internal,
      fieldName: compact ? null : name,
      field: field.id,
      idField: 'familyGuid',
      initialValues: family,
      onSubmit: submitFunc,
      modalTitle: `${name} for Family ${family.displayName}`,
      compact,
      ...(familyFieldRenderProps[field.id] || {}),
    })
  }

  let leftContent = null
  if (!hidePedigree) {
    const familyHeader = <InlineHeader
      key="name"
      size="small"
      content={showFamilyPageLink ?
        <Link to={`/project/${project.projectGuid}/family_page/${family.familyGuid}`}>{family.displayName}</Link> :
        family.displayName
      }
    />
    leftContent = [
      compact ? familyHeader : <div key="header">{familyHeader}</div>,
      <PedigreeImagePanel key="pedigree" family={family} disablePedigreeZoom={disablePedigreeZoom} compact={compact} isEditable={project.canEdit} />,
    ]
  }

  return <FamilyLayout
    useFullWidth={useFullWidth}
    compact={compact}
    annotation={annotation}
    fields={fields}
    fieldDisplay={familyField}
    leftContent={leftContent}
    rightContent={rightContent}
  />
})

Family.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  fields: PropTypes.array,
  rightContent: PropTypes.node,
  useFullWidth: PropTypes.bool,
  disablePedigreeZoom: PropTypes.bool,
  compact: PropTypes.bool,
  showFamilyPageLink: PropTypes.bool,
  hidePedigree: PropTypes.bool,
  updateFamily: PropTypes.func,
  annotation: PropTypes.node,
  disableEdit: PropTypes.bool,
  disableInternalEdit: PropTypes.bool,
}


const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = {
  updateFamily,
}

export default connect(mapStateToProps, mapDispatchToProps)(Family)

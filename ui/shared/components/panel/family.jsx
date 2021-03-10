import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Popup } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
import styled from 'styled-components'

import { updateFamily, loadAnalystOptions } from 'redux/rootReducer'
import {
  getProjectsByGuid,
  getFirstSampleByFamily,
  getUserOptionsIsLoading,
  getHasActiveVariantSampleByFamily,
} from 'redux/selectors'

import PedigreeImagePanel from './view-pedigree-image/PedigreeImagePanel'
import TextFieldView from './view-fields/TextFieldView'
import Sample from './sample'
import { ColoredIcon, InlineHeader } from '../StyledComponents'
import { Select } from '../form/Inputs'
import DataLoader from '../DataLoader'
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
} from '../../utils/constants'
import { getAnalystOptions } from '../../../pages/Project/selectors'

const FamilyGrid = styled(({ annotation, offset, ...props }) => <Grid {...props} />)`
  margin-left: ${props => ((props.annotation || props.offset) ? '25px !important' : 'inherit')};
  margin-top: ${props => (props.annotation ? '-33px !important' : 'inherit')};
`

const NoWrap = styled.div`
  white-space: nowrap;
`

const BaseFirstSample = React.memo(({ firstFamilySample, compact, hasActiveVariantSample }) =>
  <Sample
    loadedSample={firstFamilySample}
    hoverDetails={compact ? 'first loaded' : null}
    isOutdated={!hasActiveVariantSample}
  />,
)

BaseFirstSample.propTypes = {
  firstFamilySample: PropTypes.object,
  compact: PropTypes.bool,
  hasActiveVariantSample: PropTypes.bool,
}

const mapSampleDispatchToProps = (state, ownProps) => ({
  firstFamilySample: getFirstSampleByFamily(state)[ownProps.familyGuid],
  hasActiveVariantSample: getHasActiveVariantSampleByFamily(state)[ownProps.familyGuid],
})

const FirstSample = connect(mapSampleDispatchToProps)(BaseFirstSample)

const AnalystEmailDropdown = React.memo(({ load, loading, onChange, value, ...props }) =>
  <DataLoader load={load} loading={false} content>
    <Select
      loading={loading}
      additionLabel="Assigned Analyst: "
      onChange={val => onChange(val)}
      value={value}
      placeholder="Unassigned"
      search
      {...props}
    />
  </DataLoader>,
)

AnalystEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  onChange: PropTypes.func,
  value: PropTypes.any,
}

const mapDropdownStateToProps = state => ({
  loading: getUserOptionsIsLoading(state),
  options: getAnalystOptions(state),
})

const mapDropdownDispatchToProps = {
  load: loadAnalystOptions,
}

AnalystEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  onChange: PropTypes.func,
  value: PropTypes.any,
}

const EDIT_FIELDS = [
  {
    name: 'assigned_analyst_username',
    label: 'Email',
    component: connect(mapDropdownStateToProps, mapDropdownDispatchToProps)(AnalystEmailDropdown),
    width: 16,
    inline: true,
  },
]


const familyFieldRenderProps = {
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    tagOptions: FAMILY_ANALYSIS_STATUS_OPTIONS,
    tagAnnotation: (value, compact) => (compact ?
      <Popup trigger={<ColoredIcon name="stop" color={value.color} />} content={value.text} position="top center" /> :
      <ColoredIcon name="stop" color={value.color} />
    ),
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


const formatAnalysedByList = analysedByList =>
  analysedByList.map(analysedBy =>
    `${analysedBy.createdBy.displayName || analysedBy.createdBy.email} (${new Date(analysedBy.lastModifiedDate).toLocaleDateString()})`,
  ).join(', ')

export const AnalysedBy = React.memo(({ analysedByList, compact }) => {
  if (compact) {
    return [...analysedByList.reduce(
      (acc, analysedBy) => acc.add(analysedBy.createdBy.displayName || analysedBy.createdBy.email), new Set(),
    )].map(
      analysedByUser => <NoWrap key={analysedByUser}>{analysedByUser}</NoWrap>,
    )
  }
  const analystUsers = analysedByList.filter(analysedBy => analysedBy.createdBy.isAnalyst)
  const externalUsers = analysedByList.filter(analysedBy => !analysedBy.createdBy.isAnalyst)
  return [
    analystUsers.length > 0 ? <div key="analyst"><b>CMG Analysts:</b> {formatAnalysedByList(analystUsers)}</div> : null,
    externalUsers.length > 0 ? <div key="ext"><b>External Collaborators:</b> {formatAnalysedByList(externalUsers)}</div> : null,
  ]
})

AnalysedBy.propTypes = {
  analysedByList: PropTypes.array,
  compact: PropTypes.bool,
}

const getContentWidth = (useFullWidth, leftContent, rightContent) => {
  if (!useFullWidth || (leftContent && rightContent)) {
    return 10
  }
  if (leftContent || rightContent) {
    return 13
  }
  return 16
}

export const FamilyLayout = React.memo(({ leftContent, rightContent, annotation, offset, fields, fieldDisplay, useFullWidth, compact }) =>
  <div>
    {annotation}
    <FamilyGrid annotation={annotation} offset={offset}>
      <Grid.Row>
        {(leftContent || !useFullWidth) && <Grid.Column width={3}>{leftContent}</Grid.Column>}
        {compact ? fields.map(field =>
          <Grid.Column width={field.colWidth || 1} key={field.id}>{fieldDisplay(field)}</Grid.Column>,
        ) : <Grid.Column width={getContentWidth(useFullWidth, leftContent, rightContent)}>{fields.map(field => fieldDisplay(field))}</Grid.Column>
        }
        {rightContent && <Grid.Column width={3}>{rightContent}</Grid.Column>}
      </Grid.Row>
    </FamilyGrid>
  </div>,
)

FamilyLayout.propTypes = {
  fieldDisplay: PropTypes.func,
  fields: PropTypes.array,
  useFullWidth: PropTypes.bool,
  compact: PropTypes.bool,
  offset: PropTypes.bool,
  annotation: PropTypes.node,
  leftContent: PropTypes.node,
  rightContent: PropTypes.node,
}

const Family = React.memo((
  { project, family, fields = [], rightContent, compact, useFullWidth, disablePedigreeZoom, disableEdit,
    showFamilyPageLink, annotation, updateFamily: dispatchUpdateFamily, hidePedigree,
  }) => {
  if (!family) {
    return <div>Family Not Found</div>
  }

  const isEditable = !disableEdit && project.canEdit

  const familyField = (field) => {
    const renderDetails = FAMILY_FIELD_RENDER_LOOKUP[field.id]
    const submitFunc = renderDetails.submitArgs ?
      values => dispatchUpdateFamily({ ...values, ...renderDetails.submitArgs }) : dispatchUpdateFamily
    return React.createElement(renderDetails.component || TextFieldView, {
      key: field.id,
      isEditable: field.collaboratorEdit || (isEditable && field.canEdit),
      isPrivate: renderDetails.internal,
      fieldName: compact ? null : renderDetails.name,
      field: field.id,
      idField: 'familyGuid',
      initialValues: family,
      onSubmit: submitFunc,
      modalTitle: `${renderDetails.name} for Family ${family.displayName}`,
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
      <PedigreeImagePanel key="pedigree" family={family} disablePedigreeZoom={disablePedigreeZoom} compact={compact} isEditable={isEditable} />,
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

export { Family as FamilyComponent }

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
}


const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = {
  updateFamily,
}

export default connect(mapStateToProps, mapDispatchToProps)(Family)

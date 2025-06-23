import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { updateFamily } from 'redux/rootReducer'
import { getProjectsByGuid, getNotesByFamilyType } from 'redux/selectors'

import PedigreeImagePanel from '../view-pedigree-image/PedigreeImagePanel'
import BaseFieldView from '../view-fields/BaseFieldView'
import OptionFieldView from '../view-fields/OptionFieldView'
import ListFieldView from '../view-fields/ListFieldView'
import NoteListFieldView from '../view-fields/NoteListFieldView'
import SingleFieldView from '../view-fields/SingleFieldView'
import TagFieldView, { TagFieldDisplay } from '../view-fields/TagFieldView'
import TextFieldView from '../view-fields/TextFieldView'
import { InlineHeader } from '../../StyledComponents'
import {
  SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_ANALYSIS_STATUS_LOOKUP,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ASSIGNED_ANALYST,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_SUCCESS_STORY_TYPE_OPTIONS,
  successStoryTypeDisplay,
  FAMILY_FIELD_SUCCESS_STORY_TYPE,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_NAME_LOOKUP,
  FAMILY_FIELD_DISCOVERY_MONDO_ID,
  FAMILY_FIELD_OMIM_NUMBERS,
  FAMILY_FIELD_PMIDS, FAMILY_FIELD_DESCRIPTION, FAMILY_FIELD_SUCCESS_STORY, FAMILY_NOTES_FIELDS,
  FAMILY_FIELD_CODED_PHENOTYPE, FAMILY_FIELD_INTERNAL_NOTES, FAMILY_FIELD_INTERNAL_SUMMARY, FAMILY_EXTERNAL_DATA_LOOKUP,
  FAMILY_FIELD_ANALYSIS_GROUPS, FAMILY_FIELD_MONDO_ID, FAMILY_FIELD_EXTERNAL_DATA, FAMILY_EXTERNAL_DATA_OPTIONS,
} from '../../../utils/constants'
import { FirstSample, AnalystEmailDropdown, AnalysedBy, AnalysisGroups, analysisStatusIcon } from './FamilyFields'
import FamilyLayout from './FamilyLayout'

const FAMILY_NAME_FIELD_PROPS = { label: 'Name' }

const ASSIGNED_ANALYST_EDIT_FIELDS = [
  {
    name: 'assigned_analyst_username',
    label: 'Email',
    component: AnalystEmailDropdown,
    width: 16,
    inline: true,
  },
]

const mapNotesStateToProps = (state, ownProps) => ({
  notes: (getNotesByFamilyType(state)[ownProps.initialValues.familyGuid] || {})[ownProps.modalId],
})

const BASE_NOTE_FIELD = {
  canEdit: true,
  component: connect(mapNotesStateToProps)(NoteListFieldView),
}

const getNoteField = noteType => ({
  modalId: noteType,
  submitArgs: { noteType, nestedField: 'note' },
  ...BASE_NOTE_FIELD,
})

const MONDO_FIELD = {
  component: SingleFieldView,
  fieldDisplay: value => (
    <a target="_blank" rel="noreferrer" href={`http://purl.obolibrary.org/obo/MONDO_${value.replace('MONDO:', '')}`}>
      {value}
    </a>
  ),
}

const FAMILY_FIELD_RENDER_LOOKUP = {
  [FAMILY_FIELD_ANALYSIS_GROUPS]: {
    canEdit: true,
    component: AnalysisGroups,
    submitArgs: { familyField: 'analysis_groups', rawResponse: true },
    fieldDisplay: values => values.map(({ name }) => name).join(', '),
  },
  [FAMILY_FIELD_DESCRIPTION]: { canEdit: true },
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    canEdit: true,
    component: OptionFieldView,
    tagOptions: SELECTABLE_FAMILY_ANALYSIS_STATUS_OPTIONS,
    tagOptionLookup: FAMILY_ANALYSIS_STATUS_LOOKUP,
    tagAnnotation: analysisStatusIcon,
  },
  [FAMILY_FIELD_ASSIGNED_ANALYST]: {
    canEdit: true,
    formFields: ASSIGNED_ANALYST_EDIT_FIELDS,
    component: BaseFieldView,
    submitArgs: { familyField: 'assigned_analyst' },
    addConfirm: 'Are you sure you want to add the analyst to this family?',
    fieldDisplay: value => (value ? <div>{(value.fullName) ? value.fullName : value.email}</div> : ''),
  },
  [FAMILY_FIELD_ANALYSED_BY]: {
    component: BaseFieldView,
    showEmptyValues: true,
    fieldDisplay: (analysedByList, compact, familyGuid) => (
      <AnalysedBy analysedByList={analysedByList} compact={compact} familyGuid={familyGuid} />
    ),
  },
  [FAMILY_FIELD_EXTERNAL_DATA]: {
    internal: true,
    component: TagFieldView,
    tagOptions: FAMILY_EXTERNAL_DATA_OPTIONS,
    simplifiedValue: true,
    fieldDisplay: value => <TagFieldDisplay displayFieldValues={value} tagLookup={FAMILY_EXTERNAL_DATA_LOOKUP} />,
  },
  [FAMILY_FIELD_SUCCESS_STORY_TYPE]: {
    internal: true,
    component: TagFieldView,
    tagOptions: FAMILY_SUCCESS_STORY_TYPE_OPTIONS,
    simplifiedValue: true,
    fieldDisplay: value => value.map(tag => <div key={tag}>{successStoryTypeDisplay(tag)}</div>),
  },
  [FAMILY_FIELD_SUCCESS_STORY]: { internal: true },
  [FAMILY_FIELD_FIRST_SAMPLE]: {
    component: BaseFieldView,
    showEmptyValues: true,
    fieldDisplay: (loadedSample, compact, familyGuid) => <FirstSample familyGuid={familyGuid} compact={compact} />,
  },
  [FAMILY_FIELD_CODED_PHENOTYPE]: { component: SingleFieldView, canEdit: true },
  [FAMILY_FIELD_MONDO_ID]: {
    ...MONDO_FIELD,
    canEdit: true,
  },
  [FAMILY_FIELD_DISCOVERY_MONDO_ID]: {
    ...MONDO_FIELD,
    internal: true,
    canEditFamily: ({ discoveryTags }) => discoveryTags?.length > 0,
  },
  [FAMILY_FIELD_OMIM_NUMBERS]: {
    canEditFamily: ({ postDiscoveryOmimOptions }) => Object.keys(postDiscoveryOmimOptions || {}).length > 0,
    component: OptionFieldView,
    multiple: true,
    tagOptionLookupField: 'postDiscoveryOmimOptions',
    tagOptionSortField: 'category',
    formatTagOption: ({ phenotypeMimNumber, phenotypes }) => ({
      value: phenotypeMimNumber,
      category: (phenotypes || []).some(({ geneSymbol }) => geneSymbol) ? 'Gene-Related Conditions' : 'Genomic Region Conditions',
      description: (phenotypes || []).map((
        { geneSymbol, phenotypeDescription, chrom, start, end },
      ) => `${geneSymbol || `${chrom}:${start}-${end}`}: ${phenotypeDescription}`).join('; '),
    }),
    formFieldProps: {
      includeCategories: true,
    },
    tagAnnotation: ({ phenotypeMimNumber, phenotypes }) => (
      <span>
        <a target="_blank" rel="noreferrer" href={`https://www.omim.org/entry/${phenotypeMimNumber}`}>
          {phenotypeMimNumber}
        </a>
        :&nbsp;
        {(phenotypes || []).map(
          ({ geneSymbol, phenotypeDescription, phenotypeInheritance }, i) => (
            <span key={phenotypeDescription}>
              {i !== 0 && '; '}
              <b>{geneSymbol}</b>
              &nbsp;
              {phenotypeDescription}
              {phenotypeInheritance && <i>{` (${phenotypeInheritance})`}</i>}
            </span>
          ),
        )}
      </span>
    ),
  },
  [FAMILY_FIELD_PMIDS]: {
    internal: true,
    component: ListFieldView,
    itemDisplay: value => <a target="_blank" rel="noreferrer" href={`https://www.ncbi.nlm.nih.gov/pubmed/${value}`}>{value}</a>,
    addElementLabel: 'Add publication',
    addConfirm: 'This field is intended for publications which list this gene discovery on this particular family only. It is not intended for gene or phenotype level evidence, which should be added to the notes field.',
  },
  [FAMILY_FIELD_INTERNAL_NOTES]: { internal: true, submitArgs: { familyField: 'case_review_notes' } },
  [FAMILY_FIELD_INTERNAL_SUMMARY]: { internal: true, submitArgs: { familyField: 'case_review_summary' } },
  ...FAMILY_NOTES_FIELDS.reduce((acc, { id, noteType }) => ({ ...acc, [id]: getNoteField(noteType) }), {}),
}

class Family extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object,
    family: PropTypes.object.isRequired,
    fields: PropTypes.arrayOf(PropTypes.object),
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
    toggleDetails: PropTypes.func,
  }

  familyField = (field) => {
    const { family, compact, disableEdit, updateFamily: dispatchUpdateFamily, disableInternalEdit } = this.props
    const {
      submitArgs, component, canEdit, canEditFamily, internal, ...fieldProps
    } = FAMILY_FIELD_RENDER_LOOKUP[field.id]

    const name = FAMILY_FIELD_NAME_LOOKUP[field.id]
    const submitFunc = submitArgs ?
      values => dispatchUpdateFamily({ ...values, ...submitArgs }) : dispatchUpdateFamily
    return React.createElement(component || TextFieldView, {
      key: field.id,
      isEditable: !disableEdit && (canEditFamily ? canEditFamily(family) :
        (canEdit || (!disableInternalEdit && internal))),
      isPrivate: internal,
      fieldName: compact ? null : name,
      field: field.id,
      idField: 'familyGuid',
      initialValues: family,
      onSubmit: submitFunc,
      modalTitle: `${name} for Family ${family.displayName}`,
      compact,
      ...fieldProps,
    })
  }

  familyHeader = () => {
    const { family, showFamilyPageLink } = this.props
    const content = showFamilyPageLink ?
      <Link to={`/project/${family.projectGuid}/family_page/${family.familyGuid}`}>{family.displayName}</Link> :
      family.displayName
    return <InlineHeader size="small" content={content} />
  }

  render() {
    const {
      project, family, fields, rightContent, compact, useFullWidth, disablePedigreeZoom, disableEdit,
      annotation, hidePedigree, toggleDetails, updateFamily: dispatchUpdateFamily,
    } = this.props

    if (!family) {
      return <div>Family Not Found</div>
    }

    const isEditable = !disableEdit && project.canEdit

    let leftContent = null
    if (!hidePedigree) {
      const isCoreEditable = isEditable && !!project.workspaceName && !project.isAnalystProject
      const familyHeader = (
        <BaseFieldView
          field="familyId"
          idField="familyGuid"
          initialValues={family}
          fieldDisplay={this.familyHeader}
          isEditable={isCoreEditable}
          isDeletable={isCoreEditable}
          deleteConfirm={`Are you sure you want to delete ${family.displayName}? This action can not be undone`}
          formFieldProps={FAMILY_NAME_FIELD_PROPS}
          modalTitle={`Edit Family ${family.displayName}`}
          onSubmit={dispatchUpdateFamily}
        />
      )
      leftContent = (
        <span>
          {compact ? (
            <span>
              {familyHeader}
              {`(${family.individualGuids.length})`}
            </span>
          ) : (
            <span key="header">
              {familyHeader}
              <PedigreeImagePanel
                key="pedigree"
                family={family}
                disablePedigreeZoom={disablePedigreeZoom}
                isEditable={isEditable}
              />
            </span>
          )}
        </span>
      )
    }

    return (
      <FamilyLayout
        useFullWidth={useFullWidth}
        compact={compact}
        annotation={annotation}
        fields={fields}
        fieldDisplay={this.familyField}
        leftContent={leftContent}
        rightContent={rightContent}
        toggleDetails={toggleDetails}
      />
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = {
  updateFamily,
}

export default connect(mapStateToProps, mapDispatchToProps)(Family)

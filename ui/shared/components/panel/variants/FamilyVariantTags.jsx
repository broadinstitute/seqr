import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { Icon, Popup, Table, Header } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateVariantNote, updateVariantTags } from 'redux/rootReducer'
import {
  getFamiliesByGuid,
  getVariantTagNotesByFamilyVariants,
  getProjectTagTypes,
  getProjectFunctionalTagTypes,
  getVariantId,
} from 'redux/selectors'
import {
  DISCOVERY_CATEGORY_NAME,
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_ANALYSIS_STATUS_LOOKUP,
} from 'shared/utils/constants'
import PopupWithModal from '../../PopupWithModal'
import { HorizontalSpacer } from '../../Spacers'
import { ColoredComponent, NoBorderTable } from '../../StyledComponents'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { InlineToggle, BooleanCheckbox } from '../../form/Inputs'
import TagFieldView from '../view-fields/TagFieldView'
import TextFieldView from '../view-fields/TextFieldView'
import Family from '../family'

const TagTitle = styled.span`
  font-weight: bolder;
  color: #999;
`

const ColoredLink = ColoredComponent(NavLink)

const FAMILY_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_STATUS, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_NOTES, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_NOTES },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY },
]

const FAMILY_POPUP_STYLE = { maxWidth: '1200px' }

const NO_DISPLAY = { display: 'none' }

const SHORTCUT_TAGS = ['Review', 'Excluded']

const VARIANT_NOTE_FIELDS = [{
  name: 'submitToClinvar',
  label: <label>Add to <i style={{ color: 'red' }}>ClinVar</i> submission</label>, //eslint-disable-line jsx-a11y/label-has-for
  component: BooleanCheckbox,
  style: { paddingTop: '2em' },
},
{
  name: 'saveAsGeneNote',
  label: 'Add to public gene notes',
  component: BooleanCheckbox,
}]

const taggedByPopup = (tag, title) => trigger =>
  <Popup
    position="top right"
    size="tiny"
    trigger={trigger}
    header={title || 'Tagged by'}
    hoverable
    flowing
    content={
      <div>
        {tag.createdBy || 'unknown user'}
        {tag.lastModifiedDate && <span>&nbsp; on {new Date(tag.lastModifiedDate).toLocaleDateString()}</span>}
        {tag.metadata && <div>{tag.metadataTitle ? <span><b>{tag.metadataTitle}:</b> {tag.metadata}</span> : <i>{tag.metadata}</i>}</div>}
        {tag.searchHash && <div><NavLink to={`/variant_search/results/${tag.searchHash}`}>Re-run search</NavLink></div>}
      </div>
    }
  />


const ShortcutTagToggle = ({ tag, ...props }) => {
  const toggle = <InlineToggle color={tag && tag.color} divided {...props} value={tag} />
  return tag ? taggedByPopup(tag)(toggle) : toggle
}

ShortcutTagToggle.propTypes = {
  tag: PropTypes.object,
}

const ShortcutTags = ({ variantTagNotes, dispatchUpdateFamilyVariantTags, familyGuid, variantId }) => {
  const appliedShortcutTags = SHORTCUT_TAGS.reduce((acc, tagName) => {
    const appliedTag = ((variantTagNotes || {}).tags || []).find(tag => tag.name === tagName)
    return appliedTag ? { ...acc, [tagName]: appliedTag } : acc
  }, {})
  const shortcutTagFields = SHORTCUT_TAGS.map(tagName => ({
    name: tagName,
    label: tagName,
    component: ShortcutTagToggle,
    tag: appliedShortcutTags[tagName],
  }))

  const onSubmit = (values) => {
    const updatedTags = Object.keys(values).reduce((allTags, tagName) => {
      const applied = values[tagName]
      if (applied) {
        return [...allTags, { name: tagName }]
      }
      return allTags.filter(tag => tag.name !== tagName)
    }, (variantTagNotes || {}).tags || [])
    return dispatchUpdateFamilyVariantTags({ ...variantTagNotes, tags: updatedTags })
  }

  return (
    <ReduxFormWrapper
      onSubmit={onSubmit}
      form={`editShorcutTags-${variantId}-${familyGuid}`}
      initialValues={appliedShortcutTags}
      closeOnSuccess={false}
      submitOnChange
      fields={shortcutTagFields}
    />
  )
}

ShortcutTags.propTypes = {
  variantTagNotes: PropTypes.object,
  dispatchUpdateFamilyVariantTags: PropTypes.func,
  familyGuid: PropTypes.string.isRequired,
  variantId: PropTypes.string.isRequired,
}


const VariantTagField = ({ variantTagNotes, variantId, fieldName, family, ...props }) =>
  <TagFieldView
    idField="variantGuids"
    defaultId={variantId}
    modalId={family.familyGuid}
    modalTitle={`Edit Variant ${fieldName} for Family ${family.displayName} for ${
      variantId.split(',').map((vId) => {
        const [chrom, pos, ref, alt] = vId.split('-')
        return `chr${chrom}:${pos} ${ref} > ${alt}`
      }).join(', ')}`}
    modalSize="large"
    editLabel={`Edit ${fieldName}`}
    initialValues={variantTagNotes}
    compact
    isEditable
    popup={taggedByPopup}
    {...props}
  />

VariantTagField.propTypes = {
  variantTagNotes: PropTypes.object,
  fieldName: PropTypes.string,
  variantId: PropTypes.string.isRequired,
  family: PropTypes.object.isRequired,
}

const VariantNoteField = ({ action, note, variantTagNotes, family, ...props }) => {
  const values = { ...variantTagNotes, ...note }
  return (
    <div>
      <TextFieldView
        noModal
        showInLine
        isEditable
        field="note"
        modalId={family.familyGuid}
        modalTitle={`${action} Variant Note for Family ${family.displayName}`}
        additionalEditFields={VARIANT_NOTE_FIELDS}
        initialValues={values}
        idField={note ? 'noteGuid' : 'variantGuids'}
        deleteConfirm="Are you sure you want to delete this note?"
        textPopup={note && taggedByPopup(note, 'Note By')}
        {...props}
      />
    </div>
  )
}

VariantNoteField.propTypes = {
  note: PropTypes.object,
  variantTagNotes: PropTypes.object,
  action: PropTypes.string,
  family: PropTypes.object.isRequired,
}

const VariantLink = (
  { variant, family },
) =>
  <NavLink
    to={variant.variantGuid || (variant[0] || {}).variantGuid ?
      `/project/${family.projectGuid}/saved_variants/variant/${variant.length > 0 ? variant.map(sv => (sv || {}).variantGuid) : variant.variantGuid}` :
      `/variant_search/variant/${variant.variantId}/family/${family.familyGuid}`
    }
    activeStyle={NO_DISPLAY}
  >
    <Popup
      trigger={<Icon name="linkify" link />}
      content={`Go to the page for this individual variant ${(Array.isArray(variant) ?
        variant : [variant]).map(v => (v ? `chr${v.chrom}:${v.pos} ${v.ref} > ${v.alt}` : 'variant')).join(', ')} from family ${family.familyId}. Note: There is no additional information on this page, it is intended for sharing specific variants.`}
      position="right center"
      wide
    />
  </NavLink>

VariantLink.propTypes = {
  variant: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  family: PropTypes.object,
}

const FamilyVariantTags = (
  { variant, variantTagNotes, family, projectTagTypes, projectFunctionalTagTypes, dispatchUpdateVariantNote,
    dispatchUpdateFamilyVariantTags, dispatchUpdateFamilyVariantFunctionalTags, isCompoundHet, variantId },
) => (
  family ?
    <NoBorderTable basic="very" compact="very" celled>
      <Table.Body>
        <Table.Row verticalAlign="top">
          {!isCompoundHet &&
          <Table.Cell collapsing rowSpan={2}>
            <Header size="small">
              Family<HorizontalSpacer width={5} />
              <PopupWithModal
                hoverable
                style={FAMILY_POPUP_STYLE}
                position="right center"
                keepInViewPort
                trigger={
                  <ColoredLink
                    to={`/project/${family.projectGuid}/family_page/${family.familyGuid}`}
                    color={FAMILY_ANALYSIS_STATUS_LOOKUP[family[FAMILY_FIELD_ANALYSIS_STATUS]].color}
                  >
                    {family.displayName}
                  </ColoredLink>
                }
                content={<Family family={family} fields={FAMILY_FIELDS} useFullWidth disablePedigreeZoom />}
              />
            </Header>
          </Table.Cell>}
          <Table.Cell collapsing textAlign="right">
            <TagTitle>Tags:</TagTitle>
          </Table.Cell>
          {!isCompoundHet &&
          <Table.Cell collapsing>
            <ShortcutTags
              variantTagNotes={variantTagNotes}
              variantId={variantId}
              familyGuid={family.familyGuid}
              dispatchUpdateFamilyVariantTags={dispatchUpdateFamilyVariantTags}
            />
          </Table.Cell>}
          <Table.Cell>
            <VariantTagField
              field="tags"
              fieldName="Tags"
              family={family}
              variantTagNotes={variantTagNotes}
              variantId={variantId}
              tagOptions={projectTagTypes}
              onSubmit={dispatchUpdateFamilyVariantTags}
            />
            <HorizontalSpacer width={5} />
            {((variantTagNotes || {}).tags || []).some(tag => tag.category === DISCOVERY_CATEGORY_NAME) &&
            <span>
              <TagTitle>Fxnl Data:</TagTitle>
              <VariantTagField
                field="functionalData"
                fieldName="Fxnl Data"
                family={family}
                variantTagNotes={variantTagNotes}
                variantId={variantId}
                tagOptions={projectFunctionalTagTypes}
                editMetadata
                onSubmit={dispatchUpdateFamilyVariantFunctionalTags}
              />
            </span>
            }
          </Table.Cell>
          <Table.Cell collapsing textAlign="right">
            {(!Array.isArray(variant) || variantTagNotes) && <VariantLink variant={variant} family={family} />}
          </Table.Cell>
        </Table.Row>
        <Table.Row verticalAlign="top" >
          <Table.Cell collapsing textAlign="right">
            <TagTitle>Notes:</TagTitle>
          </Table.Cell>
          <Table.Cell colSpan={isCompoundHet ? 2 : 3}>
            {((variantTagNotes || {}).notes || []).map(note =>
              <VariantNoteField
                key={note.noteGuid}
                note={note}
                variantTagNotes={variantTagNotes}
                family={family}
                isDeletable
                compact
                action="Edit"
                onSubmit={dispatchUpdateVariantNote}
              />,
            )}
            <VariantNoteField
              variantTagNotes={variantTagNotes}
              defaultId={variantId}
              family={family}
              editIconName="plus"
              editLabel="Add Note"
              action="Add"
              onSubmit={dispatchUpdateVariantNote}
            />
          </Table.Cell>
        </Table.Row>
      </Table.Body>
    </NoBorderTable> : null
)

FamilyVariantTags.propTypes = {
  variant: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  variantTagNotes: PropTypes.object,
  variantId: PropTypes.string,
  family: PropTypes.object,
  projectTagTypes: PropTypes.array,
  projectFunctionalTagTypes: PropTypes.array,
  isCompoundHet: PropTypes.bool,
  dispatchUpdateVariantNote: PropTypes.func,
  dispatchUpdateFamilyVariantTags: PropTypes.func,
  dispatchUpdateFamilyVariantFunctionalTags: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => {
  const variantId = getVariantId(ownProps.variant)
  return {
    variantId,
    family: getFamiliesByGuid(state)[ownProps.familyGuid],
    projectTagTypes: getProjectTagTypes(state, ownProps),
    projectFunctionalTagTypes: getProjectFunctionalTagTypes(state, ownProps),
    variantTagNotes: ((getVariantTagNotesByFamilyVariants(state) || {})[ownProps.familyGuid] || {})[variantId],
  }
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  dispatchUpdateVariantNote: (updates) => {
    dispatch(updateVariantNote({ ...updates, variant: ownProps.variant, familyGuid: ownProps.familyGuid }))
  },
  dispatchUpdateFamilyVariantTags: (updates) => {
    dispatch(updateVariantTags({ ...updates, variant: ownProps.variant, familyGuid: ownProps.familyGuid }))
  },
  dispatchUpdateFamilyVariantFunctionalTags: (updates) => {
    dispatch(updateVariantTags({ ...updates, variant: ownProps.variant, familyGuid: ownProps.familyGuid }, 'functional_data'))
  },
})

export default connect(mapStateToProps, mapDispatchToProps)(FamilyVariantTags)

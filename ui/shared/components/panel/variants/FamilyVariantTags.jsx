import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { Icon, Popup } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateVariantNote, updateVariantTags } from 'redux/rootReducer'
import { getProjectsByGuid, getFamiliesByGuid } from 'redux/selectors'
import { DISCOVERY_CATEGORY_NAME } from 'shared/utils/constants'
import { HorizontalSpacer } from '../../Spacers'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { InlineToggle, BooleanCheckbox } from '../../form/Inputs'
import TagFieldView from '../view-fields/TagFieldView'
import TextFieldView from '../view-fields/TextFieldView'
import VariantFamily from './VariantFamily'

const TagTitle = styled.span`
  font-weight: bolder;
  margin-right: 5px;
  vertical-align: top;
`

const InlineContainer = styled.div`
  display: inline-block;
  vertical-align: top;
  
  .form {
    display: inline-block;
  }
`

const NoteContainer = styled.div`
  color: black;
  white-space: normal;
  display: inline-block;
  max-width: calc(100% - 50px);
  
  > span {
    display: flex;
  }
`

const VariantLinkContainer = styled(InlineContainer)`
  float: right;
`

const NO_DISPLAY = { display: 'none' }

const SHORTCUT_TAGS = ['Review', 'Excluded']

const VARIANT_NOTE_FIELDS = [{
  name: 'submitToClinvar',
  label: <label>Add to <i style={{ color: 'red' }}>ClinVar</i> submission</label>, //eslint-disable-line jsx-a11y/label-has-for
  component: BooleanCheckbox,
  style: { paddingTop: '2em' },
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
        {tag.searchParameters && <div><a href={tag.searchParameters} target="_blank">Re-run search</a></div>}
      </div>
    }
  />


const ShortcutTagToggle = ({ tag, ...props }) => {
  const toggle = <InlineToggle color={tag && tag.color} {...props} />
  return tag ? taggedByPopup(tag)(toggle) : toggle
}

ShortcutTagToggle.propTypes = {
  tag: PropTypes.object,
}

const ShortcutTags = ({ variant, dispatchUpdateFamilyVariantTags }) => {
  const appliedShortcutTags = SHORTCUT_TAGS.reduce((acc, tagName) => {
    const appliedTag = variant.tags.find(tag => tag.name === tagName)
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
    }, variant.tags)
    return dispatchUpdateFamilyVariantTags({ ...variant, tags: updatedTags })
  }

  return (
    <InlineContainer>
      <ReduxFormWrapper
        onSubmit={onSubmit}
        form={`editShorcutTags-${variant.variantId}`}
        initialValues={appliedShortcutTags}
        closeOnSuccess={false}
        submitOnChange
        fields={shortcutTagFields}
      />
    </InlineContainer>
  )
}

ShortcutTags.propTypes = {
  variant: PropTypes.object,
  dispatchUpdateFamilyVariantTags: PropTypes.func,
}


const VariantTagField = ({ variant, fieldName, ...props }) =>
  <TagFieldView
    idField="variantId"
    modalTitle={`Edit Variant ${fieldName} for chr${variant.chrom}:${variant.pos} ${variant.ref} > ${variant.alt}`}
    editLabel={`Edit ${fieldName}`}
    initialValues={variant}
    compact
    isEditable
    popup={taggedByPopup}
    {...props}
  />

VariantTagField.propTypes = {
  variant: PropTypes.object,
  fieldName: PropTypes.string,
}

const VariantNoteField = ({ action, note, variant, ...props }) => {
  const values = { ...variant, ...note }
  return <TextFieldView
    isEditable
    field="note"
    modalTitle={`${action} Variant Note`}
    additionalEditFields={VARIANT_NOTE_FIELDS}
    initialValues={values}
    idField={note ? 'noteGuid' : 'variantId'}
    deleteConfirm="Are you sure you want to delete this note?"
    textPopup={note && taggedByPopup(note, 'Note By')}
    {...props}
  />
}

VariantNoteField.propTypes = {
  note: PropTypes.object,
  variant: PropTypes.object,
  action: PropTypes.string,
}

const FamilyVariantTags = ({ variant, familyGuid, project, dispatchUpdateVariantNote, dispatchUpdateFamilyVariantTags }) =>
  <div>
    <InlineContainer><VariantFamily familyGuid={familyGuid} /></InlineContainer>
    <InlineContainer>
      <div>
        <TagTitle>Tags:</TagTitle>
        <HorizontalSpacer width={5} />
        <ShortcutTags variant={variant} dispatchUpdateFamilyVariantTags={dispatchUpdateFamilyVariantTags} />
        <VariantTagField
          field="tags"
          fieldName="Tags"
          variant={variant}
          tagOptions={project.variantTagTypes}
          onSubmit={dispatchUpdateFamilyVariantTags}
        />
        <HorizontalSpacer width={5} />
        {variant.tags.some(tag => tag.category === DISCOVERY_CATEGORY_NAME) &&
          <span>
            <TagTitle>Fxnl Data:</TagTitle>
            <VariantTagField
              field="functionalData"
              fieldName="Fxnl Data"
              variant={variant}
              tagOptions={project.variantFunctionalTagTypes}
              editMetadata
              onSubmit={dispatchUpdateFamilyVariantTags}
            />
            <HorizontalSpacer width={5} />
          </span>
        }
      </div>
      <div>
        <TagTitle>Notes:</TagTitle>
        <NoteContainer>
          {variant.notes.map(note =>
            <VariantNoteField
              key={note.noteGuid}
              note={note}
              variant={variant}
              isDeletable
              compact
              action="Edit"
              onSubmit={dispatchUpdateVariantNote}
            />,
          )}
          <VariantNoteField
            variant={variant}
            editIconName="plus"
            editLabel="Add Note"
            action="Add"
            onSubmit={dispatchUpdateVariantNote}
          />
        </NoteContainer>
      </div>
    </InlineContainer>
    {variant.variantGuid &&
      <VariantLinkContainer>
        <NavLink to={`/project/${variant.projectGuid}/saved_variants/variant/${variant.variantGuid}`} activeStyle={NO_DISPLAY}>
          <Popup
            trigger={<Icon name="linkify" link />}
            content="Go to the page for this individual variant. Note: There is no additional information on this page, it is intended for sharing specific variants."
            position="right center"
            wide
          />
        </NavLink>
      </VariantLinkContainer>
    }
  </div>

FamilyVariantTags.propTypes = {
  variant: PropTypes.object,
  project: PropTypes.object,
  familyGuid: PropTypes.string,
  dispatchUpdateVariantNote: PropTypes.func,
  dispatchUpdateFamilyVariantTags: PropTypes.func,
}

const EMPTY_FAMILY_TAGS = {
  tags: [],
  notes: [],
  functionalData: [],
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[getFamiliesByGuid(state)[ownProps.familyGuid].projectGuid],
  variant: { ...ownProps.variant, ...(ownProps.variant.familyTags[ownProps.familyGuid] || EMPTY_FAMILY_TAGS) },
})

const mapDispatchToProps = {
  dispatchUpdateVariantNote: updateVariantNote,
  dispatchUpdateFamilyVariantTags: updateVariantTags,
}

export default connect(mapStateToProps, mapDispatchToProps)(FamilyVariantTags)

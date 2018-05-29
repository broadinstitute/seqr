import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Popup, Icon } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateVariantNote, updateVariantTags } from 'redux/rootReducer'
import { getProject } from 'pages/Project/selectors'
import { HorizontalSpacer } from '../../Spacers'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { InlineToggle, BooleanCheckbox } from '../../form/Inputs'
import TagFieldView from '../view-fields/TagFieldView'
import TextFieldView from '../view-fields/TextFieldView'

const ShortcutToggleContainer = styled.div`
  display: inline-block;
  
  .form {
    display: inline-block;
  }
`

const TagContainer = styled.div`
  display: flex;
`

const FitContent = styled.div`
   width: fit-content;
   margin-right: 5px;
`

const TagSection = styled.div`
  display: inline-block;
  padding-bottom: 5px;
  white-space: nowrap;
  vertical-align: top;
  
  a {
    vertical-align: text-bottom;
  }
`


const ReRunSearchLink = styled.a.attrs({ target: '_blank' })`
  font-size: 12px;
  max-width: 40px;
  display: inline-block;
  line-height: .9em;
  white-space: normal;
  margin-right: 5px;
`

const NOTE_STYLES = {
  Edit: { display: 'flex', fontSize: '1.2em' },
  Add: { verticalAlign: 'middle' },
}

const SHORTCUT_TAGS = ['Review', 'Excluded']

const VARIANT_NOTE_FIELDS = [{
  name: 'submitToClinvar',
  label: <label>Add to <i style={{ color: 'red' }}>ClinVar</i> submission</label>, //eslint-disable-line jsx-a11y/label-has-for
  component: BooleanCheckbox,
  style: { paddingTop: '2em' },
}]

const taggedByPopupContent = tag =>
  <span>{tag.user || 'unknown user'}{tag.dateSaved && <span><br /> on {new Date(tag.dateSaved).toLocaleDateString()}</span>}</span>

const reRunTagSearch = tag => tag.searchParameters &&
  <ReRunSearchLink href={tag.searchParameters}>Re-run search</ReRunSearchLink>

const ShortcutTagToggle = ({ tag, ...props }) => {
  const toggle = <InlineToggle color={tag && tag.color} {...props} />
  return (
    <span>
      {tag ? <Popup
        position="top right"
        size="tiny"
        trigger={toggle}
        header="Tagged by"
        content={taggedByPopupContent(tag)}
      /> : toggle}
      <HorizontalSpacer width={5} />
      {tag && reRunTagSearch(tag)}
    </span>
  )
}

ShortcutTagToggle.propTypes = {
  tag: PropTypes.object,
}

const ShortcutTags = ({ variant, dispatchUpdateVariantTags }) => {
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
    return dispatchUpdateVariantTags({ ...variant, tags: updatedTags })
  }

  return (
    <ShortcutToggleContainer>
      <ReduxFormWrapper
        onSubmit={onSubmit}
        form={`editShorcutTags-${variant.variantId}`}
        initialValues={appliedShortcutTags}
        closeOnSuccess={false}
        submitOnChange
        fields={shortcutTagFields}
      />
    </ShortcutToggleContainer>
  )
}

ShortcutTags.propTypes = {
  variant: PropTypes.object,
  dispatchUpdateVariantTags: PropTypes.func,
}


const VariantTagField = ({ variant, fieldName, ...props }) =>
  <TagFieldView
    idField="variantId"
    modalTitle={`Edit Variant ${fieldName} for chr${variant.chrom}:${variant.pos} ${variant.ref} > ${variant.alt}`}
    editLabel={`Edit ${fieldName}`}
    initialValues={variant}
    compact
    isEditable
    popupContent={taggedByPopupContent}
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
    style={NOTE_STYLES[action]}
    initialValues={values}
    idField={note ? 'noteGuid' : 'variantId'}
    deleteConfirm="Are you sure you want to delete this note?"
    textPopupContent={note && taggedByPopupContent(note)}
    {...props}
  />
}

VariantNoteField.propTypes = {
  note: PropTypes.object,
  variant: PropTypes.object,
  action: PropTypes.string,
}

const VariantTags = ({ variant, project, updateVariantNote: dispatchUpdateVariantNote, updateVariantTags: dispatchUpdateVariantTags }) =>
  <TagContainer>
    <FitContent>
      <TagSection>
        <b>Tags:<HorizontalSpacer width={10} /></b>
        <ShortcutTags variant={variant} dispatchUpdateVariantTags={dispatchUpdateVariantTags} />
        <VariantTagField
          field="tags"
          fieldName="Tags"
          variant={variant}
          tagOptions={project.variantTagTypes}
          hiddenTags={SHORTCUT_TAGS}
          onSubmit={dispatchUpdateVariantTags}
          tagAnnotation={reRunTagSearch}
        />
        <HorizontalSpacer width={5} />
      </TagSection>
      {variant.tags.some(tag => tag.category === 'CMG Discovery Tags') &&
        <TagSection>
          <b>Fxnl Data:<HorizontalSpacer width={5} /></b>
          <VariantTagField
            field="functionalData"
            fieldName="Fxnl Data"
            variant={variant}
            tagOptions={project.variantFunctionalTagTypes}
            editMetadata
            onSubmit={dispatchUpdateVariantTags}
            tagAnnotation={tag => tag.metadata &&
              <Popup
                position="top center"
                trigger={<Icon name="info circle" size="large" color="black" fitted />}
                header={tag.metadataTitle}
                content={tag.metadata}
              />
            }
          />
          <HorizontalSpacer width={5} />
        </TagSection>
      }
    </FitContent>
    <FitContent><b>Notes:</b></FitContent>
    <div>
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
    </div>
  </TagContainer>

VariantTags.propTypes = {
  variant: PropTypes.object,
  project: PropTypes.object,
  updateVariantNote: PropTypes.func,
  updateVariantTags: PropTypes.func,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = {
  updateVariantNote, updateVariantTags,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantTags)

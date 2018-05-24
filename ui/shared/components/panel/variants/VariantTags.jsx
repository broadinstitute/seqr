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
  white-space: normal
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

const ShortcutTagToggle = ({ value, ...props }) =>
  <span>
    <InlineToggle value={value.isApplied} color={value.color} label={value.name} {...props} />
    <HorizontalSpacer width={5} />
    {reRunTagSearch(value)}
    {value.searchParameters && <HorizontalSpacer width={5} />}
  </span>

ShortcutTagToggle.propTypes = {
  value: PropTypes.any,
}

const SHORTCUT_TAG_FIELDS = SHORTCUT_TAGS.map(tagName => ({
  name: tagName,
  component: ShortcutTagToggle,
}))

const ShortcutTags = ({ variant, dispatchUpdateVariantTags }) => {
  const appliedShortcutTags = SHORTCUT_TAGS.reduce((acc, tagName) => {
    const appliedTag = variant.tags.find(tag => tag.name === tagName)
    return { ...acc, [tagName]: appliedTag ? { ...appliedTag, isApplied: true } : { name: tagName, isApplied: false } }
  }, {})
  const onSubmit = (values) => {
    const updatedTags = Object.keys(values).reduce((allTags, tagName) => {
      const applied = values[tagName]
      if (applied === true) {
        return [...allTags, { name: tagName }]
      } else if (applied === false) {
        return allTags.filter(tag => tag.name !== tagName)
      }
      return allTags
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
        fields={SHORTCUT_TAG_FIELDS}
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

const VariantNoteField = ({ action, ...props }) =>
  <TextFieldView
    isEditable
    field="note"
    modalTitle={`${action} Variant Note`}
    additionalEditFields={VARIANT_NOTE_FIELDS}
    style={NOTE_STYLES[action]}
    {...props}
  />

VariantNoteField.propTypes = {
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
          initialValues={note}
          isDeletable
          compact
          idField="noteGuid"
          onSubmit={dispatchUpdateVariantNote}
          action="Edit"
          deleteConfirm="Are you sure you want to delete this note?"
          textPopupContent={taggedByPopupContent(note)}
        />,
      )}
      <VariantNoteField
        editIconName="plus"
        editLabel="Add Note"
        idField="variantId"
        action="Add"
        initialValues={variant}
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

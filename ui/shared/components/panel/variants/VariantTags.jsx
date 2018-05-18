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

const TagContainer = styled.span`
  display: flex;
  
  .fit-content {
    min-width: fit-content;
  } 
`

const ReRunSearchLink = styled.a.attrs({ target: '_blank' })`
  font-size: 12px;
  max-width: 40px;
  display: inline-block;
  line-height: .9em;
  vertical-align: bottom;
`

const NOTE_STYLE = { display: 'flex', fontSize: '1.2em' }
const ADD_NOTE_STYLE = { verticalAlign: 'middle' }

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

const SHORTCUT_TAG_FIELDS = [{
  name: 'tags',
  isArrayField: true,
  component: ShortcutTagToggle,
}]

const ShortcutTags = ({ variant, dispatchUpdateVariantTags }) => {
  const appliedShortcutTags = SHORTCUT_TAGS.map((tagName) => {
    const appliedTag = variant.tags.find(tag => tag.name === tagName)
    return appliedTag ? { ...appliedTag, isApplied: true } : { name: tagName, isApplied: false }
  })
  const initialValues = { tags: appliedShortcutTags }
  const onSubmit = ({ tags }) => {
    const updatedTags = tags.reduce((allTags, applied, index) => {
      if (applied === true) {
        return [...allTags, { name: appliedShortcutTags[index].name }]
      } else if (applied === false) {
        return allTags.filter(tag => tag.name !== appliedShortcutTags[index].name)
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
        initialValues={initialValues}
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


const VariantTags = ({ variant, project, updateVariantNote: dispatchUpdateVariantNote, updateVariantTags: dispatchUpdateVariantTags }) =>
  <TagContainer>
    <span className="fit-content">
      <b>Tags:<HorizontalSpacer width={10} /></b>
      <ShortcutTags variant={variant} dispatchUpdateVariantTags={dispatchUpdateVariantTags} />
      <TagFieldView
        field="tags"
        idField="variantId"
        modalTitle="Edit Variant Tags"
        editLabel="Edit Tags"
        initialValues={variant}
        tagOptions={project.variantTagTypes}
        hiddenTags={SHORTCUT_TAGS}
        compact
        isEditable
        popupContent={taggedByPopupContent}
        onSubmit={dispatchUpdateVariantTags}
        tagAnnotation={reRunTagSearch}
      />
      <HorizontalSpacer width={5} />
      {variant.tags.some(tag => tag.category === 'CMG Discovery Tags') &&
        <span>
          <b>Fxnl Data:<HorizontalSpacer width={10} /></b>
          <TagFieldView
            field="functionalData"
            idField="variantId"
            modalTitle="Edit Variant Functional Data"
            initialValues={variant}
            tagOptions={project.variantFunctionalTagTypes}
            editMetadata
            compact
            isEditable
            popupContent={taggedByPopupContent}
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
        </span>
      }
      <b>Notes:<HorizontalSpacer width={10} /></b>
    </span>
    <span>
      {variant.notes.map(note =>
        <TextFieldView
          key={note.noteGuid}
          initialValues={note}
          isEditable
          isDeletable
          compact
          field="note"
          idField="noteGuid"
          onSubmit={dispatchUpdateVariantNote}
          modalTitle="Edit Variant Note"
          textEditorAdditionalFields={VARIANT_NOTE_FIELDS}
          deleteConfirm="Are you sure you want to delete this note?"
          textPopupContent={taggedByPopupContent(note)}
          style={NOTE_STYLE}
        />,
      )}
      <TextFieldView
        isEditable
        editIconName="plus"
        editLabel="Add Note"
        field="note"
        idField="variantId"
        modalTitle="Add Variant Note"
        initialValues={variant}
        additionalEditFields={VARIANT_NOTE_FIELDS}
        onSubmit={dispatchUpdateVariantNote}
        style={ADD_NOTE_STYLE}
      />
    </span>
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

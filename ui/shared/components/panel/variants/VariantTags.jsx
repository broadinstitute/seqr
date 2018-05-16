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

const InlineForm = styled.div`
  display: inline-block;
  
  .form {
    display: inline-block;
  }
  
  .field.inline {
    padding-right: 10px;
  }
`

const SHORTCUT_TAGS = ['Review', 'Excluded']

const VARIANT_NOTE_FIELDS = [{
  name: 'submitToClinvar',
  label: <label>Add to <i style={{ color: 'red' }}>ClinVar</i> submission</label>, //eslint-disable-line jsx-a11y/label-has-for
  component: BooleanCheckbox,
  style: { paddingTop: '2em' },
}]

const taggedByPopupContent = tag =>
  <span>{tag.user || 'unknown user'}{tag.dateSaved && <br />}{tag.dateSaved}</span>

const ShortcutTagToggle = ({ value, ...props }) =>
  <InlineToggle value={value.isApplied} color={value.color} label={value.name} {...props} />

ShortcutTagToggle.propTypes = {
  value: PropTypes.any,
}

const ShortcutTags = ({ variant, dispatchUpdateVariantTags }) => {
  const appliedShortcutTags = SHORTCUT_TAGS.map((tagName) => {
    const appliedTag = variant.tags.find(tag => tag.name === tagName)
    return appliedTag ? { ...appliedTag, isApplied: true } : { name: tagName, isApplied: false }
  })
  return (
    <InlineForm>
      <ReduxFormWrapper
        onSubmit={({ tags }) => {
          const updatedTags = tags.reduce((allTags, applied, index) => {
            if (applied === true) {
              return [...allTags, { name: appliedShortcutTags[index].name }]
            } else if (applied === false) {
              return allTags.filter(tag => tag.name !== appliedShortcutTags[index].name)
            }
            return allTags
          }, variant.tags)
          return dispatchUpdateVariantTags({ ...variant, tags: updatedTags })
        }}
        form={`editShorcutTags-${variant.variantId}`}
        initialValues={{ tags: appliedShortcutTags }}
        closeOnSuccess={false}
        submitOnChange
        fields={[{
          name: 'tags',
          isArrayField: true,
          component: ShortcutTagToggle,
        }]}
      />
    </InlineForm>
  )
}

ShortcutTags.propTypes = {
  variant: PropTypes.object,
  dispatchUpdateVariantTags: PropTypes.func,
}


const VariantTags = ({ variant, project, updateVariantNote: dispatchUpdateVariantNote, updateVariantTags: dispatchUpdateVariantTags }) =>
  <span style={{ display: 'flex' }}>
    <span style={{ minWidth: 'fit-content' }}>
      <b>Tags:</b>
      <HorizontalSpacer width={10} />
      <ShortcutTags variant={variant} dispatchUpdateVariantTags={dispatchUpdateVariantTags} />
      <TagFieldView
        field="tags"
        idField="variantId"
        modalTitle="Edit Variant Tags"
        initialValues={variant}
        tagOptions={project.variantTagTypes}
        hiddenTags={SHORTCUT_TAGS}
        compact
        isEditable
        popupContent={taggedByPopupContent}
        onSubmit={dispatchUpdateVariantTags}
        tagAnnotation={tag => tag.searchParameters &&
          <a href={tag.searchParameters} target="_blank">
            <Icon name="search" title="Re-run search" fitted />
          </a>
        }
      />
      <HorizontalSpacer width={5} />
      {variant.tags.some(tag => tag.category === 'CMG Discovery Tags') &&
        <span>
          <b>Fxnl Data:</b>
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
      <b>Notes:</b>
      <HorizontalSpacer width={5} />
      <TextFieldView
        isEditable
        editIconName="plus"
        field="note"
        idField="variantId"
        modalTitle="Add Variant Note"
        initialValues={{ variantId: variant.variantId }}
        additionalEditFields={VARIANT_NOTE_FIELDS}
        onSubmit={dispatchUpdateVariantNote}
      />
      <HorizontalSpacer width={5} />
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
          style={{ display: 'flex', fontSize: '1.2em' }}
        />,
      )}
    </span>
  </span>

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

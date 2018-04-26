import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Label, Popup, Icon } from 'semantic-ui-react'

import { updateVariantNote, updateVariantTags } from 'redux/rootReducer'
import { getProject } from 'pages/Project/reducers'
import { HorizontalSpacer } from '../../Spacers'
import EditTextButton from '../../buttons/EditTextButton'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import { InlineToggle, BooleanCheckbox } from '../../form/Inputs'
import TagFieldView from '../view-fields/TagFieldView'
import TextFieldView from '../view-fields/TextFieldView'


const CLINSIG_COLOR = {
  pathogenic: 'red',
  'risk factor': 'orange',
  'likely pathogenic': 'red',
  benign: 'green',
  'likely benign': 'green',
  protective: 'green',
}

const SHORTCUT_TAGS = ['Review', 'Excluded']

const taggedByPopupContent = tag =>
  <span>{tag.user || 'unknown user'}{tag.dateSaved && <br />}{tag.dateSaved}</span>

const variantNoteFields = [{
  name: 'submitToClinvar',
  label: <label>Add to <i style={{ color: 'red' }}>ClinVar</i> submission</label>, //eslint-disable-line jsx-a11y/label-has-for
  component: BooleanCheckbox,
  style: { paddingTop: '2em' },
}]


const VariantTags = ({ variant, project, updateVariantNote: dispatchUpdateVariantNote, updateVariantTags: dispatchUpdateVariantTags }) =>
  <span style={{ display: 'flex' }}>
    <span style={{ minWidth: 'fit-content' }}>
      {variant.clinvar.variantId &&
        <span>
          <b>ClinVar:</b>
          {variant.clinvar.clinsig.split('/').map(clinsig =>
            <a key={clinsig} target="_blank" href={`http://www.ncbi.nlm.nih.gov/clinvar/variation/${variant.clinvar.variantId}`}>
              <HorizontalSpacer width={5} />
              <Label color={CLINSIG_COLOR[clinsig] || 'grey'} size="small" horizontal>{clinsig}</Label>
            </a>,
          )}
        </span>
      }
      <b>Tags:</b>
      <HorizontalSpacer width={10} />
      {SHORTCUT_TAGS.map((tagName) => {
        const selectedTag = variant.tags.find(tag => tag.name === tagName)
        return (
          <DispatchRequestButton
            key={tagName}
            onSubmit={values => dispatchUpdateVariantTags(
              { ...variant,
                tags: values.checked ? [...variant.tags, { name: tagName }] : variant.tags.filter(tag => tag.name !== tagName) },
            )}
          >
            <InlineToggle color={(selectedTag || {}).color} value={selectedTag} label={tagName} />
          </DispatchRequestButton>
        )
      })}
      <TagFieldView
        field="tags"
        idField="variantId"
        initialValues={variant}
        tagOptions={project.variantTagTypes}
        hiddenTags={SHORTCUT_TAGS}
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
            initialValues={variant}
            tagOptions={project.variantFunctionalTagTypes}
            editMetadata
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
      <EditTextButton
        iconName="plus"
        fieldId="note"
        modalTitle="Add Variant Note"
        initialValues={{ variantId: variant.variantId }}
        additionalEditFields={variantNoteFields}
        onSubmit={dispatchUpdateVariantNote}
        modalId={`addVariantNote${variant.variantId}`}
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
          fieldId="note"
          textEditorId={`variantNote${note.noteGuid}`}
          textEditorSubmit={dispatchUpdateVariantNote}
          textEditorTitle="Edit Variant Note"
          textEditorAdditionalFields={variantNoteFields}
          deleteConfirm="Are you sure you want to delete this note?"
          textPopupContent={taggedByPopupContent(note)}
          style={{ display: 'flex' }}
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

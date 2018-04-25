import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Label, Popup, Icon } from 'semantic-ui-react'

import { updateVariantNote, updateVariantTags } from 'redux/rootReducer'
import { getProject } from 'pages/Project/reducers'
import { HorizontalSpacer } from '../../Spacers'
import EditTextButton from '../../buttons/EditTextButton'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import { InlineToggle } from '../../form/Inputs'
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

const taggedByPopupContent = tag =>
  <span>{tag.user || 'unknown user'}{tag.dateSaved && <br />}{tag.dateSaved}</span>


const ToggleNoteForClinvar = ({ note, dispatchUpdateVariantNote }) =>
  <DispatchRequestButton
    confirmDialog="Are you sure you want to change whether this note should be submitted to clinvar?"
    onSubmit={values => dispatchUpdateVariantNote({ ...note, submitToClinvar: values.checked })}
  >
    <InlineToggle
      color="red"
      checked={note.submitToClinvar}
      label="For Clinvar"
    />
  </DispatchRequestButton>

ToggleNoteForClinvar.propTypes = {
  note: PropTypes.object,
  dispatchUpdateVariantNote: PropTypes.func,
}


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
      <TagFieldView
        field="tags"
        idField="variantId"
        initialValues={variant}
        tagOptions={project.variantTagTypes}
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
        onSubmit={values => dispatchUpdateVariantNote({ variantId: variant.variantId, ...values })}
        modalId={`addVariantNote${variant.variantI}`}
      />
      <HorizontalSpacer width={5} />
    </span>
    <span>
      {variant.notes.map(note =>
        <TextFieldView
          key={note.noteGuid}
          initialText={note.note}
          isEditable
          isDeletable
          compact
          fieldId="note"
          textEditorId={`variantNote${note.noteGuid}`}
          textEditorSubmit={values => dispatchUpdateVariantNote({ ...note, ...values })}
          textEditorTitle="Edit Variant Note"
          deleteConfirm="Are you sure you want to delete this note?"
          textPopupContent={taggedByPopupContent(note)}
          textAnnotation={<ToggleNoteForClinvar note={note} dispatchUpdateVariantNote={dispatchUpdateVariantNote} />}
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

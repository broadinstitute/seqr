import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import TextFieldView from '../view-fields/TextFieldView'

const noteRequired = value => (value ? undefined : 'Note is required')

const userCanEdit = (note, user) => (
  note.createdBy === user.displayName || note.createdBy === user.email
)

const CORE_PROPS = {
  field: 'note',
  fieldValidator: noteRequired,
}

const NOTE_ANNOTATION_STYLE = { color: 'gray' }
const noteAnnotation = note => note.createdBy && (
  <i style={NOTE_ANNOTATION_STYLE}>
    By {note.createdBy} ({new Date(note.lastModifiedDate).toLocaleDateString()})
  </i>
)

const NoteListFieldView = React.memo(({ notes, initialValues, idField, isEditable, modalTitle, fieldName, getTextPopup, user, ...props }) => {
  const nonEmptyInitialValues = initialValues || {}
  const addField =
    <TextFieldView
      {...props}
      {...CORE_PROPS}
      fieldName={fieldName}
      isEditable={isEditable}
      editIconName="plus"
      editLabel="Add Note"
      idField={idField}
      modalTitle={`Add ${modalTitle}`}
      initialValues={nonEmptyInitialValues}
    />
  return (
    <div>
      {fieldName && addField}
      {(notes || nonEmptyInitialValues.notes || []).map(note =>
        <div key={note.noteGuid}>
          <TextFieldView
            {...props}
            {...CORE_PROPS}
            initialValues={note}
            idField="noteGuid"
            textAnnotation={!getTextPopup && noteAnnotation(note)}
            textPopup={getTextPopup && getTextPopup(note)}
            isEditable={isEditable && userCanEdit(note, user)}
            isDeletable={isEditable && userCanEdit(note, user)}
            modalTitle={`Edit ${modalTitle}`}
            deleteConfirm="Are you sure you want to delete this note?"
          />
        </div>,
      )}
      {!fieldName && <div>{addField}</div>}
    </div>
  )
})

NoteListFieldView.propTypes = {
  initialValues: PropTypes.object,
  notes: PropTypes.array,
  idField: PropTypes.string,
  fieldName: PropTypes.string,
  modalTitle: PropTypes.string,
  isEditable: PropTypes.bool,
  getTextPopup: PropTypes.func,
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(NoteListFieldView)

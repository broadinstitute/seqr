import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import TextFieldView from '../view-fields/TextFieldView'

const NOTE_STYLE = { display: 'block' }

const userCanEdit = (note, user) => (
  note.createdBy ? (note.createdBy === user.displayName || note.createdBy === user.email) : true
)

const NoteListFieldView = React.memo(({ initialValues, newIdField, modalTitleBase, getTextAnnotation, getTextPopup, user, ...props }) => {
  const { notes } = initialValues || {}

  return (
    <div>
      {(notes || []).map(note =>
        <TextFieldView
          key={note.noteGuid}
          initialValues={note}
          field="note"
          idField="noteGuid"
          textAnnotation={getTextAnnotation && getTextAnnotation(note)}
          textPopup={getTextPopup && getTextPopup(note)}
          isEditable={userCanEdit(note, user)}
          isDeletable={userCanEdit(note, user)}
          modalTitle={`Edit ${modalTitleBase}`}
          deleteConfirm="Are you sure you want to delete this note?"
          style={NOTE_STYLE}
          {...props}
        />,
      )}
      <TextFieldView
        isEditable
        editIconName="plus"
        editLabel="Add Note"
        field="note"
        idField={newIdField}
        modalTitle={`Add ${modalTitleBase}`}
        initialValues={initialValues}
        style={NOTE_STYLE}
        {...props}
      />
    </div>
  )
})

NoteListFieldView.propTypes = {
  initialValues: PropTypes.object,
  newIdField: PropTypes.string,
  modalTitleBase: PropTypes.string,
  getTextAnnotation: PropTypes.func,
  getTextPopup: PropTypes.func,
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(NoteListFieldView)

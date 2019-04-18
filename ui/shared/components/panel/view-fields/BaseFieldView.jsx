import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import StaffOnlyIcon from '../../icons/StaffOnlyIcon'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import DeleteButton from '../../buttons/DeleteButton'
import UpdateButton from '../../buttons/UpdateButton'
import { HorizontalSpacer } from '../../Spacers'

const FieldValue = styled.div`
  padding-bottom: ${props => (props.compact ? 0 : '15px')}; 
  padding-left: ${props => (props.compact ? 0 : '22px')};
  padding-right: ${props => (props.fieldName ? '20px' : '5px')};
  display: ${props => ((props.fieldName && !props.compact) ? 'block' : 'inline-block')};
`

const BaseFieldView = (props) => {
  if (props.isVisible !== undefined && !props.isVisible) {
    return null
  }
  if (props.isPrivate && !props.user.isStaff) {
    return null
  }
  const fieldValue = props.initialValues[props.field]
  const hasValue = (fieldValue && (!Object.getOwnPropertyNames(fieldValue).includes('length') || fieldValue.length > 0)) || props.showEmptyValues
  if (!props.isEditable && !hasValue) {
    return null
  }
  const fieldId = props.initialValues[props.idField]
  const modalId = props.isEditable ? `edit-${fieldId || 'new'}-${props.field}-${props.modalId}` : null

  const editButton = props.isEditable && (props.formFields ?
    <UpdateButton
      key="edit"
      modalTitle={props.modalTitle}
      modalId={modalId}
      modalSize={props.modalSize}
      buttonText={props.editLabel}
      editIconName={props.editIconName}
      onSubmit={props.onSubmit}
      initialValues={props.initialValues}
      formFields={props.formFields}
      formContainer={<div style={props.modalStyle} />}
      showErrorPanel={props.showErrorPanel}
      confirmDialog={props.addConfirm}
      size="tiny"
    />
    : (
      <DispatchRequestButton
        key="edit"
        buttonContent={<Icon link size="small" name="plus" />}
        onSubmit={() => props.onSubmit(props.initialValues)}
        confirmDialog={props.addConfirm}
      />
    ))
  const deleteButton = props.isDeletable && (
    <DeleteButton
      key="delete"
      initialValues={props.initialValues}
      onSubmit={props.onSubmit}
      confirmDialog={props.deleteConfirm}
      size="tiny"
    />
  )
  const buttons = [editButton, deleteButton]

  return (
    <span style={props.style || {}}>
      {props.isPrivate && <StaffOnlyIcon />}
      {props.fieldName && [
        <b key="name">{props.fieldName}{hasValue ? ':' : null}<HorizontalSpacer width={10} /></b>,
        ...buttons,
        props.compact && (buttons.some(b => b) ? <HorizontalSpacer width={10} key="hs" /> : null),
        !props.compact && <br key="br" />,
      ]}
      {
        hasValue && !props.hideValue &&
        <FieldValue compact={props.compact} fieldName={props.fieldName}>
          {props.fieldDisplay(fieldValue, props.compact, fieldId)}
        </FieldValue>
      }
      {!props.fieldName && buttons}
    </span>)
}

BaseFieldView.propTypes = {
  fieldDisplay: PropTypes.func,
  formFields: PropTypes.array,
  isVisible: PropTypes.any,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  isDeletable: PropTypes.bool,
  onSubmit: PropTypes.func,
  modalTitle: PropTypes.string,
  addConfirm: PropTypes.string,
  deleteConfirm: PropTypes.string,
  fieldName: PropTypes.string,
  field: PropTypes.string.isRequired,
  idField: PropTypes.string,
  initialValues: PropTypes.object,
  compact: PropTypes.bool,
  style: PropTypes.object,
  editLabel: PropTypes.string,
  editIconName: PropTypes.string,
  hideValue: PropTypes.bool,
  showEmptyValues: PropTypes.bool,
  user: PropTypes.object,
  modalStyle: PropTypes.object,
  showErrorPanel: PropTypes.bool,
  modalId: PropTypes.string,
  modalSize: PropTypes.string,
}

BaseFieldView.defaultProps = {
  fieldDisplay: val => val,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(BaseFieldView)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Segment, Popup } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import DeleteButton from '../../buttons/DeleteButton'
import UpdateButton from '../../buttons/UpdateButton'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink } from '../../StyledComponents'
import FormWrapper from '../../form/FormWrapper'

const FieldValue = styled.div`
  padding-bottom: ${props => (props.compact ? 0 : '15px')}; 
  padding-left: ${props => (props.compact ? 0 : '22px')};
  padding-right: ${props => (props.fieldName ? '20px' : '5px')};
  display: ${props => (((props.fieldName && !props.compact) || props.blockDisplay) ? 'block' : 'inline-block')};
  max-width: calc(100% - ${props => (props.hasButtons ? '60' : '0')}px);
`

class BaseFieldView extends React.PureComponent {

  static propTypes = {
    showInLine: PropTypes.bool,
    fieldDisplay: PropTypes.func,
    formFields: PropTypes.arrayOf(PropTypes.object),
    formFieldProps: PropTypes.object,
    isVisible: PropTypes.bool,
    isPrivate: PropTypes.bool,
    isEditable: PropTypes.bool,
    isDeletable: PropTypes.bool,
    isRequired: PropTypes.bool,
    onSubmit: PropTypes.func,
    modalTitle: PropTypes.string,
    addConfirm: PropTypes.string,
    deleteConfirm: PropTypes.string,
    fieldName: PropTypes.string,
    field: PropTypes.string.isRequired,
    idField: PropTypes.string,
    initialValues: PropTypes.object,
    fieldValue: PropTypes.any, // eslint-disable-line react/forbid-prop-types
    compact: PropTypes.bool,
    style: PropTypes.object,
    editLabel: PropTypes.string,
    editIconName: PropTypes.string,
    hideValue: PropTypes.bool,
    showEmptyValues: PropTypes.bool,
    user: PropTypes.object,
    modalStyle: PropTypes.object,
    modalPopup: PropTypes.object,
    modalTrigger: PropTypes.node,
    showErrorPanel: PropTypes.bool,
    modalId: PropTypes.string,
    modalSize: PropTypes.string,
    defaultId: PropTypes.string,
    additionalEditFields: PropTypes.arrayOf(PropTypes.object),
    blockDisplay: PropTypes.bool,
  }

  static defaultProps = {
    fieldDisplay: val => val,
  }

  state = { showInLineButton: true }

  toggleButtonVisibility = () => {
    this.setState(prevState => ({
      showInLineButton: !prevState.showInLineButton,
    }))
  }

  getFieldId = () => {
    const { initialValues, idField, defaultId } = this.props
    return initialValues[idField] || defaultId
  }

  getFormFields = () => {
    const { field, formFieldProps, additionalEditFields = [] } = this.props
    return [...additionalEditFields, { name: field, ...formFieldProps }]
  }

  getEditButton = () => {
    const {
      initialValues, modalId, isEditable, formFields, showInLine, editLabel, editIconName, onSubmit, showErrorPanel,
      addConfirm, modalTitle, modalSize, modalStyle, field, formFieldProps, modalTrigger, modalPopup,
    } = this.props
    const { showInLineButton } = this.state

    if (!isEditable) {
      return null
    }

    if (formFields || formFieldProps) {
      const fieldId = this.getFieldId()
      const fieldModalId = `edit_-_${fieldId || 'new'}_-_${field}_-_${modalId}`
      return showInLine ? (
        <span key="edit">
          {showInLineButton ? (
            <ButtonLink
              size="tiny"
              labelPosition={editLabel && 'right'}
              icon={editIconName || 'write'}
              content={editLabel}
              onClick={this.toggleButtonVisibility}
            />
          ) : (
            <Segment compact>
              <FormWrapper
                noModal
                inline
                key="edit"
                onSubmit={onSubmit}
                onSubmitSucceeded={this.toggleButtonVisibility}
                onCancel={this.toggleButtonVisibility}
                modalName={fieldModalId}
                initialValues={initialValues}
                fields={formFields || this.getFormFields()}
                showErrorPanel={showErrorPanel}
              />
            </Segment>
          )}
        </span>
      ) : (
        <UpdateButton
          showInLine={showInLine}
          key="edit"
          modalTitle={modalTitle}
          modalId={fieldModalId}
          formMetaId={fieldId}
          modalSize={modalSize}
          trigger={modalTrigger}
          buttonText={editLabel}
          editIconName={editIconName}
          modalPopup={modalPopup}
          onSubmit={onSubmit}
          initialValues={initialValues}
          formFields={formFields || this.getFormFields()}
          formContainer={<div style={modalStyle} />}
          showErrorPanel={showErrorPanel}
          confirmDialog={addConfirm}
          size="tiny"
        />
      )
    }
    return (
      <DispatchRequestButton
        key="edit"
        buttonContent={<Icon link size="small" name="plus" />}
        onSubmit={this.submitInitialValues}
        confirmDialog={addConfirm}
      />
    )
  }

  submitInitialValues = () => {
    const { onSubmit, initialValues } = this.props
    return onSubmit(initialValues)
  }

  render() {
    const {
      isVisible, isPrivate, isEditable, isDeletable, user, field, initialValues, fieldValue: propFieldValue, style,
      showEmptyValues, onSubmit, deleteConfirm, fieldName, compact, hideValue, fieldDisplay, isRequired, blockDisplay,
    } = this.props
    const { showInLineButton } = this.state

    if (isVisible !== undefined && !isVisible) {
      return null
    }
    if (isPrivate && !user.isAnalyst) {
      return null
    }
    const fieldValue = propFieldValue || initialValues[field]
    const hasValue = (fieldValue && (!Object.getOwnPropertyNames(fieldValue).includes('length') || fieldValue.length > 0)) || showEmptyValues || isRequired
    if (!isEditable && !hasValue) {
      return null
    }

    const editButton = this.getEditButton()

    const deleteButton = isDeletable && (
      <DeleteButton
        size="tiny"
        key="delete"
        initialValues={initialValues}
        onSubmit={onSubmit}
        confirmDialog={deleteConfirm}
      />
    )
    const buttons = [editButton, deleteButton]
    const hasButtons = editButton || deleteButton
    const content = [
      isPrivate && (
        <Popup
          key="private"
          trigger={<Icon name="lock" size="small" />}
          position="top center"
          size="small"
          content="Only visible to internal users."
        />
      ),
      isRequired && <Icon key="required" name="asterisk" size="small" />,
      fieldName && [
        <b key="name">{`${fieldName}${hasValue ? ':' : ''}`}</b>,
        <HorizontalSpacer key="spacer" width={10} />,
        ...buttons,
        compact && (hasButtons ? <HorizontalSpacer width={10} key="hs" /> : null),
        !compact && <br key="br" />,
      ],
      hasValue && !hideValue && showInLineButton && (
        <FieldValue key="value" compact={compact} fieldName={fieldName} hasButtons={hasButtons} blockDisplay={blockDisplay}>
          {fieldDisplay(fieldValue, compact, this.getFieldId())}
        </FieldValue>
      ),
      !fieldName && buttons,
    ].filter(val => val)
    return style ? <span style={style}>{content}</span> : content
  }

}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(BaseFieldView)

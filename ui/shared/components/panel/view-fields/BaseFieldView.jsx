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
import ReduxFormWrapper from '../../form/ReduxFormWrapper'

const FieldValue = styled.div`
  padding-bottom: ${props => (props.compact ? 0 : '15px')}; 
  padding-left: ${props => (props.compact ? 0 : '22px')};
  padding-right: ${props => (props.fieldName ? '20px' : '5px')};
  display: ${props => ((props.fieldName && !props.compact) ? 'block' : 'inline-block')};
  max-width: calc(100% - ${props => (props.hasButtons ? '60' : '0')}px);
`

class BaseFieldView extends React.PureComponent {
  constructor(props) {
    super(props)
    this.state = {
      showInLineButton: true,
    }
    this.toggleButtonVisibility = this.toggleButtonVisibility.bind(this)
  }

  toggleButtonVisibility() {
    this.setState({
      showInLineButton: !this.state.showInLineButton,
    })
  }

  render() {
    if (this.props.isVisible !== undefined && !this.props.isVisible) {
      return null
    }
    if (this.props.isPrivate && !this.props.user.isAnalyst) {
      return null
    }
    const fieldValue = this.props.fieldValue || this.props.initialValues[this.props.field]
    const hasValue = (fieldValue && (!Object.getOwnPropertyNames(fieldValue).includes('length') || fieldValue.length > 0)) || this.props.showEmptyValues
    if (!this.props.isEditable && !hasValue) {
      return null
    }
    const fieldId = this.props.initialValues[this.props.idField] || this.props.defaultId
    const modalId = this.props.isEditable ? `edit-${fieldId || 'new'}-${this.props.field}-${this.props.modalId}` : null

    let editButton
    if (this.props.isEditable) {
      if (this.props.formFields) {
        editButton =
          this.props.showInLine ?
            <span key="edit">
              {this.state.showInLineButton ?
                <ButtonLink
                  size="tiny"
                  labelPosition={this.props.editLabel && 'right'}
                  icon={this.props.editIconName || 'write'}
                  content={this.props.editLabel}
                  onClick={this.toggleButtonVisibility}
                />
                :
                <Segment compact>
                  <ReduxFormWrapper
                    noModal
                    inline
                    key="edit"
                    onSubmit={this.props.onSubmit}
                    onSubmitSucceeded={this.toggleButtonVisibility}
                    form={this.props.modalId}
                    initialValues={this.props.initialValues}
                    fields={this.props.formFields}
                    showErrorPanel={this.props.showErrorPanel}
                  />
                </Segment>
              }
            </span>
            :
            <UpdateButton
              showInLine={this.props.showInLine}
              key="edit"
              modalTitle={this.props.modalTitle}
              modalId={modalId}
              modalSize={this.props.modalSize}
              buttonText={this.props.editLabel}
              editIconName={this.props.editIconName}
              onSubmit={this.props.onSubmit}
              initialValues={this.props.initialValues}
              formFields={this.props.formFields}
              formContainer={<div style={this.props.modalStyle} />}
              showErrorPanel={this.props.showErrorPanel}
              confirmDialog={this.props.addConfirm}
              size="tiny"
            />
      } else {
        editButton =
          <DispatchRequestButton
            key="edit"
            buttonContent={<Icon link size="small" name="plus" />}
            onSubmit={() => this.props.onSubmit(this.props.initialValues)}
            confirmDialog={this.props.addConfirm}
          />
      }
    }

    const deleteButton = this.props.isDeletable && (
      <DeleteButton
        size="tiny"
        key="delete"
        initialValues={this.props.initialValues}
        onSubmit={this.props.onSubmit}
        confirmDialog={this.props.deleteConfirm}
      />
    )
    const buttons = [editButton, deleteButton]
    const hasButtons = editButton || deleteButton

    return (
      <span style={this.props.style || {}}>
        {this.props.isPrivate && <Popup
          trigger={<Icon name="lock" size="small" />}
          position="top center"
          size="small"
          content="Only visible to internal users."
        />}
        {this.props.fieldName && [
          <b key="name">{this.props.fieldName}{hasValue ? ':' : null}<HorizontalSpacer width={10} /></b>,
          ...buttons,
          this.props.compact && (hasButtons ? <HorizontalSpacer width={10} key="hs" /> : null),
          !this.props.compact && <br key="br" />,
        ]}
        {
          hasValue && !this.props.hideValue && this.state.showInLineButton &&
          <FieldValue compact={this.props.compact} fieldName={this.props.fieldName} hasButtons={hasButtons}>
            {this.props.fieldDisplay(fieldValue, this.props.compact, fieldId)}
          </FieldValue>
        }
        {!this.props.fieldName && buttons}
      </span>)
  }
}

BaseFieldView.propTypes = {
  showInLine: PropTypes.bool,
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
  fieldValue: PropTypes.any,
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
  defaultId: PropTypes.string,
}

BaseFieldView.defaultProps = {
  fieldDisplay: val => val,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(BaseFieldView)

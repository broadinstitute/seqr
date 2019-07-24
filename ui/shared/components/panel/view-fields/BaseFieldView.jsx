import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Segment } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import StaffOnlyIcon from '../../icons/StaffOnlyIcon'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import DeleteButton from '../../buttons/DeleteButton'
import UpdateButton from '../../buttons/UpdateButton'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink } from '../..//StyledComponents'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'

const FieldValue = styled.div`
  padding-bottom: ${props => (props.compact ? 0 : '15px')}; 
  padding-left: ${props => (props.compact ? 0 : '22px')};
  padding-right: ${props => (props.fieldName ? '20px' : '5px')};
  display: ${props => ((props.fieldName && !props.compact) ? 'block' : 'inline-block')};
`

class BaseFieldView extends React.Component {
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
    if (this.props.isPrivate && !this.props.user.isStaff) {
      return null
    }
    const fieldValue = this.props.initialValues[this.props.field]
    const hasValue = (fieldValue && (!Object.getOwnPropertyNames(fieldValue).includes('length') || fieldValue.length > 0)) || this.props.showEmptyValues
    if (!this.props.isEditable && !hasValue) {
      return null
    }
    const fieldId = this.props.initialValues[this.props.idField]
    const modalId = this.props.isEditable ? `edit-${fieldId || 'new'}-${this.props.field}-${this.props.modalId}` : null

    const onSubmit = this.props.showInLine ?
      this.toggleButtonVisibility : this.props.onSubmit
    // TODO combine the following two functions ==================================
    // this.toggleButtonVisibility
    // this.props.onSubmit

    const updateButton = this.props.showInLine ?
      <div>
        {this.state.showInLineButton &&
        <ButtonLink
          icon="write"
          onClick={this.toggleButtonVisibility}
        />}
        {!this.state.showInLineButton &&
        <Segment>
          <ReduxFormWrapper
            onSubmit={onSubmit}
            form={this.props.modalId}
            initialValues={this.props.initialValues}
            fields={this.props.formFields}
            showErrorPanel={this.props.showErrorPanel}
            confirmDialog={this.props.confirmDialog}
            confirmCloseIfNotSaved
          />
        </Segment>
        }
      </div>
      : (
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
      )

    const editButton = this.props.isEditable && (this.props.formFields ?
      updateButton
      : (
        <DispatchRequestButton
          key="edit"
          buttonContent={<Icon link size="small" name="plus" />}
          onSubmit={() => this.props.onSubmit(this.props.initialValues)}
          confirmDialog={this.props.addConfirm}
        />
      ))

    const deleteButton = this.props.isDeletable && (
      <DeleteButton
        key="delete"
        initialValues={this.props.initialValues}
        onSubmit={this.props.onSubmit}
        confirmDialog={this.props.deleteConfirm}
        size="tiny"
      />
    )
    const buttons = [editButton, deleteButton]

    return (
      <span style={this.props.style || {}}>
        {this.props.isPrivate && <StaffOnlyIcon />}
        {this.props.fieldName && [
          <b key="name">{this.props.fieldName}{hasValue ? ':' : null}<HorizontalSpacer width={10} /></b>,
          ...buttons,
          this.props.compact && (buttons.some(b => b) ? <HorizontalSpacer width={10} key="hs" /> : null),
          !this.props.compact && <br key="br" />,
        ]}
        {
          hasValue && !this.props.hideValue && this.state.showInLineButton &&
          <FieldValue compact={this.props.compact} fieldName={this.props.fieldName}>
            {this.props.fieldDisplay(fieldValue, this.props.compact, fieldId)}
          </FieldValue>
        }
        {!this.props.fieldName && buttons}
      </span>)
  }

  shouldComponentUpdate(nextProps, nextState) {
    return nextState.showInLineButton !== this.state.showInLineButton
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
  confirmDialog: PropTypes.string,
}

BaseFieldView.defaultProps = {
  fieldDisplay: val => val,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(BaseFieldView)

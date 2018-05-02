import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import StaffOnlyIcon from '../../icons/StaffOnlyIcon'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import Modal from '../../modal/Modal'
import { HorizontalSpacer } from '../../Spacers'

const hasValue = val => val && (!('length' in Object.getOwnPropertyNames(val)) || val.length > 0)

const BaseFieldView = (props) => {
  if (props.isVisible !== undefined && !props.isVisible) {
    return null
  }
  const fieldValue = props.initialValues[props.fieldId]
  if (!props.isEditable && !hasValue(fieldValue)) {
    return null
  }

  return (
    <span style={props.style || {}}>
      {props.isPrivate && <StaffOnlyIcon />}
      {props.fieldName && <b>{props.fieldName}{hasValue(fieldValue) && ':'}<HorizontalSpacer width={20} /></b>}
      {props.isEditable && (props.formFields ?
        <Modal title={props.modalTitle} modalName={props.modalId} trigger={
          <a role="button" tabIndex="0">
            <Icon link size="small" name="write" />
          </a>
        }
        >
          <ReduxFormWrapper
            onSubmit={props.onSubmit}
            form={props.modalId}
            initialValues={props.initialValues}
            fields={props.formFields}
            confirmCloseIfNotSaved
          />
        </Modal>
        : (
          <DispatchRequestButton
            buttonContent={<Icon link size="small" name="plus" />}
            onSubmit={() => props.onSubmit(props.initialValues)}
            confirmDialog={props.addConfirm}
          />
        )
      )}
      {props.isDeletable &&
        <DispatchRequestButton
          buttonContent={<Icon link size="small" name="trash" />}
          onSubmit={() => props.onSubmit({ ...props.initialValues, delete: true })}
          confirmDialog={props.deleteConfirm}
        />
      }
      {props.fieldName && <br />}
      {
        hasValue(fieldValue) &&
        <div style={{ paddingBottom: props.compact ? 0 : '15px', paddingLeft: props.isDeletable || props.compact ? 0 : ' 22px', display: props.fieldName ? 'block' : 'inline-block' }}>
          {props.fieldDisplay(fieldValue)}
        </div>
      }
    </span>)
}

BaseFieldView.propTypes = {
  fieldDisplay: PropTypes.func.isRequired,
  formFields: PropTypes.array,
  isVisible: PropTypes.any,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  isDeletable: PropTypes.bool,
  modalId: PropTypes.string,
  onSubmit: PropTypes.func,
  modalTitle: PropTypes.string,
  addConfirm: PropTypes.string,
  deleteConfirm: PropTypes.string,
  fieldName: PropTypes.string,
  fieldId: PropTypes.string,
  initialValues: PropTypes.object,
  compact: PropTypes.bool,
  style: PropTypes.object,
}

export default BaseFieldView

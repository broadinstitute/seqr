import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
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
  if (props.isPrivate && !props.user.is_staff) {
    return null
  }
  const fieldValue = props.initialValues[props.field]
  if (!props.isEditable && !hasValue(fieldValue)) {
    return null
  }
  const modalId = props.isEditable ? `edit-${props.initialValues[props.idField] || 'new'}-${props.field}` : null
  return (
    <span style={props.style || {}}>
      {props.isPrivate && <StaffOnlyIcon />}
      {props.fieldName && <b>{props.fieldName}{hasValue(fieldValue) && ':'}<HorizontalSpacer width={20} /></b>}
      {props.isEditable && (props.formFields ?
        <Modal title={props.modalTitle} modalName={modalId} trigger={
          <a role="button" tabIndex="0">
            {
              props.editLabel ?
                <div>
                  <div style={{ cursor: 'pointer', display: 'inline-block', padding: '5px 10px 10px 12px' }}>{props.editLabel}</div>
                  <Icon link size="small" name={props.editIconName || 'write'} />
                </div>
                : <Icon link size="small" name={props.editIconName || 'write'} />
            }
          </a>
        }
        >
          <ReduxFormWrapper
            onSubmit={props.onSubmit}
            form={modalId}
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
        hasValue(fieldValue) && !props.hideValue &&
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
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(BaseFieldView)

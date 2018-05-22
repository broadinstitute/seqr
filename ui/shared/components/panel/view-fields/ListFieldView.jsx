import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'
import StaffOnlyIcon from 'shared/components/icons/StaffOnlyIcon'
import SendRequestButton from 'shared/components/buttons/send-request/SendRequestButton'
import { HorizontalSpacer } from 'shared/components/Spacers'

const ListFieldView = (props) => {
  if (props.isVisible !== undefined && !props.isVisible) {
    return null
  }
  if (!props.isEditable && !props.values.length > 0) {
    return null
  }

  return (
    <span>
      {props.isPrivate && <StaffOnlyIcon />}
      {props.fieldName && (
        props.values.length > 0 ? <b>{props.fieldName}:</b> : <b>{props.fieldName}</b>
      )}
      <HorizontalSpacer width={20} />
      {props.isEditable && props.addItemUrl &&
        <SendRequestButton
          button={<a role="button"><Icon link size="small" name="plus" /></a>}
          requestUrl={props.addItemUrl}
          showConfirmDialogBeforeSending={props.confirmAddMessage}
          getDataToSend={() => props.addItemData}
          onRequestSuccess={props.onItemAdded}
          onRequestError={(error) => { console.log(error) }}
        />
      }
      <br />
      {
        props.values.length > 0 &&
        <div style={{ padding: '0px 0px 15px 22px' }}>
          {props.values.join(', ')}
          <br />
        </div>
      }
    </span>)
}

ListFieldView.propTypes = {
  isVisible: PropTypes.any,
  isPrivate: PropTypes.bool,
  isEditable: PropTypes.bool,
  addItemUrl: PropTypes.string,
  addItemData: PropTypes.object,
  onItemAdded: PropTypes.func,
  fieldName: PropTypes.string.isRequired,
  values: PropTypes.arrayOf(PropTypes.string),
  confirmAddMessage: PropTypes.string,
}

export default ListFieldView

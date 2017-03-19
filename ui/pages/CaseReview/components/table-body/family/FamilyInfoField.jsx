/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Icon } from 'semantic-ui-react'

import StaffOnlyIcon from 'shared/components/icons/StaffOnlyIcon'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { showEditFamilyInfoModal } from '../../../reducers/rootReducer'

const handleEditClick = props =>
  props.showEditFamilyInfoModal(props.editFamilyInfoModalTitle, props.initialText, props.editFamilyInfoModalSubmitUrl)

const FamilyInfoField = (props) => {
  if (!props.isEditable && !props.initialText) {
    return null
  }

  return <span>
    {props.isPrivate ? <StaffOnlyIcon /> : null}
    <b>{props.fieldName}: </b>
    <HorizontalSpacer width={20} />
    {props.isEditable ? <a tabIndex="0" onClick={() => handleEditClick(props)}><Icon link name="write" /></a> : null}
    <br />
    {props.initialText ?
      <div style={{ padding: '0px 0px 15px 22px', maxWidth: '550px', wordWrap: 'break-word' }} dangerouslySetInnerHTML={{ __html: props.initialText }} /> : null
    }
  </span>
}

export { FamilyInfoField as FamilyInfoFieldComponent }

FamilyInfoField.propTypes = {
  isPrivate: React.PropTypes.bool,
  isEditable: React.PropTypes.bool,
  fieldName: React.PropTypes.string.isRequired,
  initialText: React.PropTypes.string.isRequired,
  editFamilyInfoModalTitle: React.PropTypes.string,
  editFamilyInfoModalSubmitUrl: React.PropTypes.string,

  showEditFamilyInfoModal: React.PropTypes.func,
}

const mapDispatchToProps = dispatch => bindActionCreators({
  showEditFamilyInfoModal,
}, dispatch)


export default connect(null, mapDispatchToProps)(FamilyInfoField)

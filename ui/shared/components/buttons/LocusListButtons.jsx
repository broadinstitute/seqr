import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { updateLocusList } from 'redux/rootReducer'

import { LocusListItemsLoader } from '../LocusListLoader'
import UpdateButton from './UpdateButton'
import DeleteButton from './DeleteButton'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_ITEMS_FIELD } from '../../utils/constants'


const FIELDS = LOCUS_LIST_FIELDS.concat(
  [LOCUS_LIST_ITEMS_FIELD],
).filter(field => field.isEditable).map(({ isEditable, width, fieldDisplay, ...fieldProps }) => fieldProps)

const UpdateLocusList = ({ locusList, size, onSubmit }) =>
  <UpdateButton
    modalTitle="Edit Gene List"
    modalId={`editLocusList-${locusList.locusListGuid}`}
    onSubmit={onSubmit}
    initialValues={locusList}
    formFields={FIELDS}
    formContainer={<LocusListItemsLoader locusList={locusList} />}
    size={size}
    showErrorPanel
  />


UpdateLocusList.propTypes = {
  onSubmit: PropTypes.func,
  locusList: PropTypes.object,
  size: PropTypes.string,
}

const CreateLocusList = ({ onSubmit }) =>
  <UpdateButton
    modalTitle="Create a New Gene List"
    modalId="createLocusList"
    buttonText="Create New Gene List"
    editIconName="plus"
    onSubmit={onSubmit}
    formFields={FIELDS}
    showErrorPanel
  />

CreateLocusList.propTypes = {
  onSubmit: PropTypes.func,
}

const DeleteLocusList = ({ locusList, onSubmit, size, iconOnly }) =>
  <DeleteButton
    initialValues={locusList}
    onSubmit={onSubmit}
    confirmDialog={<div className="content">Are you sure you want to delete <b>{locusList.name}</b></div>}
    buttonText={iconOnly ? null : 'Delete Gene List'}
    size={size}
  />

DeleteLocusList.propTypes = {
  onSubmit: PropTypes.func,
  locusList: PropTypes.object,
  iconOnly: PropTypes.bool,
  size: PropTypes.string,
}

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export { CreateLocusList, UpdateLocusList, DeleteLocusList }

export const CreateLocusListButton = connect(null, mapDispatchToProps)(CreateLocusList)
export const UpdateLocusListButton = connect(null, mapDispatchToProps)(UpdateLocusList)
export const DeleteLocusListButton = connect(null, mapDispatchToProps)(DeleteLocusList)


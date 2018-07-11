import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { updateLocusList } from 'redux/rootReducer'
import ReduxFormWrapper from '../form/ReduxFormWrapper'
import Modal from '../modal/Modal'
import ButtonLink from './ButtonLink'
import DeleteButton from './DeleteButton'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_GENE_FIELD } from '../../utils/constants'

const ID = 'createLocusList'

const FIELDS = LOCUS_LIST_FIELDS.concat([LOCUS_LIST_GENE_FIELD]).filter(field => field.isEditable).map(
  ({ isEditable, width, fieldDisplay, ...fieldProps }) => fieldProps,
)

const CreateLocusList = ({ onSubmit }) =>
  <Modal title="Create a New Gene List" modalName={ID} trigger={<ButtonLink>Create New Gene List</ButtonLink>}>
    <ReduxFormWrapper
      onSubmit={onSubmit}
      form={ID}
      fields={FIELDS}
      confirmCloseIfNotSaved
    />
  </Modal>

CreateLocusList.propTypes = {
  onSubmit: PropTypes.func,
}

const DeleteLocusList = ({ locusList, onSubmit }) =>
  <DeleteButton
    initialValues={locusList}
    onSubmit={onSubmit}
    confirmDialog={<div className="content">Are you sure you want to delete <b>{locusList.name}</b></div>}
    buttonText="Delete Gene List"
  />

DeleteLocusList.propTypes = {
  onSubmit: PropTypes.func,
  locusList: PropTypes.object,
}

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export const CreateLocusListButton = connect(null, mapDispatchToProps)(CreateLocusList)
export const DeleteLocusListButton = connect(null, mapDispatchToProps)(DeleteLocusList)


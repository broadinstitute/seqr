import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { updateLocusList } from 'redux/rootReducer'
import ReduxFormWrapper from '../form/ReduxFormWrapper'
import Modal from '../modal/Modal'
import ButtonLink from './ButtonLink'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_GENE_FIELD } from '../../utils/constants'

const ID = 'createLocusList'

const FIELDS = LOCUS_LIST_FIELDS.concat([LOCUS_LIST_GENE_FIELD]).filter(field => field.isEditable).map(
  ({ isEditable, width, fieldDisplay, ...fieldProps }) => fieldProps,
)

const CreateLocusListButton = ({ onSubmit }) =>
  <Modal title="Create a New Gene List" modalName={ID} trigger={<ButtonLink>Create New Gene List</ButtonLink>}>
    <ReduxFormWrapper
      onSubmit={onSubmit}
      form={ID}
      fields={FIELDS}
      confirmCloseIfNotSaved
    />
  </Modal>

CreateLocusListButton.propTypes = {
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export default connect(null, mapDispatchToProps)(CreateLocusListButton)


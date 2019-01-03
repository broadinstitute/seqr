import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { getProjectsFamiliesSearchInput } from '../selectors'

const SAVED_SEARCH_FIELDS = [{ name: 'name', label: 'Search Name', validate: validators.required }]

const SaveSearchButton = ({ search }) =>
  <UpdateButton
    formFields={SAVED_SEARCH_FIELDS}
    onSubmit={console.log}
    initialValues={search}
    disabled={!search}
    modalId="saveSearch"
    modalTitle="Save Search"
    buttonText="Save Search"
    editIconName="save"
  />

SaveSearchButton.propTypes = {
  search: PropTypes.object,
}

const mapStateToProps = state => ({
  search: getProjectsFamiliesSearchInput(state),
})

export default connect(mapStateToProps)(SaveSearchButton)

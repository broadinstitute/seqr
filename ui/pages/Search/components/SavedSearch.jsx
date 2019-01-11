import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { saveSearch } from '../reducers'
import { getProjectsFamiliesSearchInput } from '../selectors'

const SAVED_SEARCH_FIELDS = [{ name: 'name', label: 'Search Name', validate: validators.required }]

const FormButtonContainer = styled.div`
  position: absolute;
  right: 150px;
  bottom: 10px;
`

const SaveSearchButton = ({ search, onSubmit }) =>
  <FormButtonContainer>
    <UpdateButton
      formFields={SAVED_SEARCH_FIELDS}
      onSubmit={onSubmit}
      initialValues={search}
      disabled={!search}
      modalId="saveSearch"
      modalTitle="Save Search"
      buttonText="Save Search"
      editIconName="save"
    />
  </FormButtonContainer>

SaveSearchButton.propTypes = {
  search: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  search: getProjectsFamiliesSearchInput(state),
})

const mapDispatchToProps = {
  onSubmit: saveSearch,
}

export default connect(mapStateToProps, mapDispatchToProps)(SaveSearchButton)

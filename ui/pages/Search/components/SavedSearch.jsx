import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { Dropdown } from 'shared/components/form/Inputs'
import { saveSearch } from '../reducers'
import { getSearchInput, getSavedSearchesByGuid } from '../selectors'

const SAVED_SEARCH_FIELDS = [{ name: 'name', label: 'Search Name', validate: validators.required }]

const FormButtonContainer = styled.div`
  position: absolute;
  right: 150px;
  bottom: 10px;
`

const SaveSearch = ({ search, onSubmit }) =>
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

SaveSearch.propTypes = {
  search: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  search: getSearchInput(state),
})

const mapDispatchToProps = {
  onSubmit: saveSearch,
}

export const SaveSearchButton = connect(mapStateToProps, mapDispatchToProps)(SaveSearch)


const SavedSearches = ({ savedSearchesByGuid, value, onChange }) => {
  const savedSearches = Object.values(savedSearchesByGuid)
  const options = savedSearches.map(search => ({ text: search.name, value: search.savedSearchGuid }))
  const selectedSearch = savedSearches.find(search => JSON.stringify(search) === JSON.stringify(value))
  return (
    <Dropdown
      selection
      inline
      placeholder="Select a Saved Search"
      value={(selectedSearch || {}).savedSearchGuid}
      onChange={val => onChange(savedSearchesByGuid[val].search)}
      options={options}
    />
  )
}

SavedSearches.propTypes = {
  savedSearchesByGuid: PropTypes.object,
  value: PropTypes.object,
  onChange: PropTypes.func,
}

const mapDropdownStateToProps = state => ({
  savedSearchesByGuid: getSavedSearchesByGuid(state),
})

export const SavedSearchDropdown = connect(mapDropdownStateToProps)(SavedSearches)

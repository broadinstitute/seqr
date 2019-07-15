import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import DataLoader from 'shared/components/DataLoader'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/ReduxFormWrapper'
import { Dropdown, BooleanCheckbox } from 'shared/components/form/Inputs'
import { saveSearch, loadSavedSearches } from '../reducers'
import {
  getSearchInput,
  getSavedSearchesByGuid,
  getSavedSearchesIsLoading,
  getSavedSearchesLoadingError,
  getCurrentSavedSearch,
  getSavedSearchOptions,
} from '../selectors'

const SEARCH_NAME_FIELD = { name: 'name', label: 'Search Name', validate: validators.required }
const SAVED_SEARCH_FIELDS = [SEARCH_NAME_FIELD]
const EXISTING_SAVED_SEARCH_FIELDS = [
  SEARCH_NAME_FIELD,
  { name: 'delete', label: 'Delete saved search?', component: BooleanCheckbox },
]

const FormButtonContainer = styled.div`
  position: absolute;
  right: 150px;
  bottom: 10px;
`

const ButtonDropdown = styled(Dropdown).attrs({ button: true, basic: true })`
  .ui.basic.button.dropdown {
    color: ${props => props.color} !important;
    box-shadow: 0px 0px 0px 1px ${props => props.color} inset !important;
  }
`

const SaveSearch = ({ search, savedSearch, onSubmit }) =>
  <FormButtonContainer>
    <UpdateButton
      formFields={savedSearch ? EXISTING_SAVED_SEARCH_FIELDS : SAVED_SEARCH_FIELDS}
      onSubmit={onSubmit}
      initialValues={savedSearch || search}
      disabled={!search}
      modalId="saveSearch"
      modalTitle={savedSearch ? 'Edit Saved Search' : 'Save Search'}
      buttonText={savedSearch ? 'Edit Saved Search' : 'Save Search'}
      editIconName={savedSearch ? 'write' : 'save'}
    />
  </FormButtonContainer>

SaveSearch.propTypes = {
  search: PropTypes.object,
  savedSearch: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  search: getSearchInput(state),
  savedSearch: getCurrentSavedSearch(state),
})

const mapDispatchToProps = {
  onSubmit: saveSearch,
}

export const SaveSearchButton = connect(mapStateToProps, mapDispatchToProps)(SaveSearch)


const SavedSearches = ({ options, savedSearchesByGuid, selectedSearch, load, loading, errorMessage, onChange }) =>
  <DataLoader load={load} errorMessage={errorMessage} loading={false} content>
    <ButtonDropdown
      color="black"
      inline
      includeCategories
      loading={loading}
      placeholder="Select a Saved Search"
      value={(selectedSearch || {}).savedSearchGuid}
      onChange={val => onChange(savedSearchesByGuid[val].search)}
      options={options}
    />
  </DataLoader>

SavedSearches.propTypes = {
  options: PropTypes.array,
  savedSearchesByGuid: PropTypes.object,
  selectedSearch: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  errorMessage: PropTypes.string,
  onChange: PropTypes.func,
}

const mapDropdownStateToProps = state => ({
  options: getSavedSearchOptions(state),
  savedSearchesByGuid: getSavedSearchesByGuid(state),
  selectedSearch: getCurrentSavedSearch(state),
  loading: getSavedSearchesIsLoading(state),
  errorMessage: getSavedSearchesLoadingError(state),
})

const mapDropdownDispatchToProps = {
  load: loadSavedSearches,
}

export const SavedSearchDropdown = connect(mapDropdownStateToProps, mapDropdownDispatchToProps)(SavedSearches)

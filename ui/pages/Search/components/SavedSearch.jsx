import React from 'react'
import isEqual from 'lodash/isEqual'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'
import styled from 'styled-components'

import DataLoader from 'shared/components/DataLoader'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/FormHelpers'
import { Select, BooleanCheckbox } from 'shared/components/form/Inputs'
import { saveSearch, loadSavedSearches } from '../reducers'
import {
  getSavedSearchesByGuid,
  getSavedSearchesIsLoading,
  getSavedSearchesLoadingError,
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

const SUBSCRIPTION = { values: true }

const isSameSearch = ({ locus: locus1, ...search1 }, { locus: locus2, ...search2 }) => (
  isEqual(search1, search2) && (
    locus1?.locusListGuid ? locus1.locusListGuid === locus2.locusListGuid : isEqual(locus1, locus2)
  )
)

const CurrentSavedSearchProvider = ({ element, ...props }) => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => {
      const currentSavedSearch = values.search && Object.values(props.savedSearchesByGuid).find(
        ({ search }) => isSameSearch(search, values.search),
      )
      return React.createElement(element, { currentSavedSearch, search: values.search, ...props })
    }}
  </FormSpy>
)

CurrentSavedSearchProvider.propTypes = {
  savedSearchesByGuid: PropTypes.object,
  element: PropTypes.object,
}

const SaveSearch = React.memo(({ search, currentSavedSearch, onSubmit }) => (
  <FormButtonContainer>
    <UpdateButton
      formFields={currentSavedSearch ? EXISTING_SAVED_SEARCH_FIELDS : SAVED_SEARCH_FIELDS}
      onSubmit={onSubmit}
      initialValues={currentSavedSearch || search}
      disabled={!search}
      modalId="saveSearch"
      modalTitle={currentSavedSearch ? 'Edit Saved Search' : 'Save Search'}
      buttonText={currentSavedSearch ? 'Edit Saved Search' : 'Save Search'}
      editIconName={currentSavedSearch ? 'write' : 'save'}
    />
  </FormButtonContainer>
))

SaveSearch.propTypes = {
  search: PropTypes.object,
  currentSavedSearch: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  savedSearchesByGuid: getSavedSearchesByGuid(state),
})

const mapDispatchToProps = {
  onSubmit: saveSearch,
}

export const SaveSearchButton = connect(mapStateToProps, mapDispatchToProps)(props => (
  <CurrentSavedSearchProvider {...props} element={SaveSearch} />
))

const selectSearch = (onChange, savedSearchesByGuid) => val => onChange(
  savedSearchesByGuid[val] ? savedSearchesByGuid[val].search : {},
)

const SavedSearches = React.memo((
  { options, savedSearchesByGuid, currentSavedSearch, load, loading, errorMessage, onChange },
) => (
  <DataLoader load={load} errorMessage={errorMessage} loading={false} content>
    <Select
      includeCategories
      loading={loading}
      placeholder="Select a Saved Search"
      value={(currentSavedSearch || {}).savedSearchGuid}
      onChange={selectSearch(onChange, savedSearchesByGuid)}
      options={options}
    />
  </DataLoader>
))

SavedSearches.propTypes = {
  options: PropTypes.arrayOf(PropTypes.object),
  savedSearchesByGuid: PropTypes.object,
  currentSavedSearch: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  errorMessage: PropTypes.string,
  onChange: PropTypes.func,
}

const mapDropdownStateToProps = state => ({
  options: getSavedSearchOptions(state),
  savedSearchesByGuid: getSavedSearchesByGuid(state),
  loading: getSavedSearchesIsLoading(state),
  errorMessage: getSavedSearchesLoadingError(state),
})

const mapDropdownDispatchToProps = {
  load: loadSavedSearches,
}

export const SavedSearchDropdown = connect(mapDropdownStateToProps, mapDropdownDispatchToProps)(props => (
  <CurrentSavedSearchProvider {...props} element={SavedSearches} />
))

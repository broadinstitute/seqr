import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusListItems } from 'redux/rootReducer'
import { getLocusListIsLoading } from 'redux/selectors'
import { Dropdown, BaseSemanticInput } from 'shared/components/form/Inputs'
import { parseLocusListItems } from 'shared/components/LocusListLoader'
import DataLoader from 'shared/components/DataLoader'
import { getSearchedProjectsLocusLists } from '../../selectors'


const BaseLocusListSelector = ({ value, projectLocusLists, loadLocusList }) =>
  <Dropdown
    inline
    selection
    label="Gene List"
    defaultValue={value.locusListGuid}
    onChange={loadLocusList}
    options={projectLocusLists.map(locusList => ({ text: locusList.name, value: locusList.locusListGuid }))}
  />

const mapStateToProps = state => ({
  projectLocusLists: getSearchedProjectsLocusLists(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    loadLocusList: (locusListGuid) => {
      if (locusListGuid) {
        dispatch(loadLocusListItems(locusListGuid, responseJson =>
          ownProps.onChange(parseLocusListItems(responseJson.locusListsByGuid[locusListGuid], responseJson.genesById)),
        ))
      }
    },
  }
}

BaseLocusListSelector.propTypes = {
  value: PropTypes.object,
  projectLocusLists: PropTypes.array,
  loadLocusList: PropTypes.func,
}

export const LocusListSelector = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListSelector)

export const BaseLoadedLocusListField = ({ value, loading, loadLocusList, ...props }) =>
  <DataLoader contentId={value.locusListGuid} loading={loading} load={loadLocusList} content hideError>
    <BaseSemanticInput {...props} value={value.display} inputType="TextArea" />
  </DataLoader>

BaseLoadedLocusListField.propTypes = {
  value: PropTypes.object,
  loading: PropTypes.bool,
  loadLocusList: PropTypes.func,
}

const mapLoaderStateToProps = state => ({
  loading: getLocusListIsLoading(state),
})

export const LoadedLocusListField = connect(mapLoaderStateToProps, mapDispatchToProps)(BaseLoadedLocusListField)

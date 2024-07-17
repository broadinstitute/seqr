import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Popup, Icon } from 'semantic-ui-react'
import styled from 'styled-components'

import { loadUserOptions, updateFamily } from 'redux/rootReducer'
import { loadProjectAnalysisGroups } from 'redux/utils/reducerUtils'
import {
  getSamplesByFamily,
  getUserOptionsIsLoading,
  getHasActiveSearchSampleByFamily,
  getUserOptions,
  getProjectAnalysisGroupOptions,
  getAnalysisGroupsByFamily,
  getAnalysisGroupIsLoading,
} from 'redux/selectors'
import { SNP_DATA_TYPE, FAMILY_ANALYSED_BY_DATA_TYPES } from 'shared/utils/constants'

import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import TagFieldView from '../view-fields/TagFieldView'
import Sample from '../sample'
import { ColoredIcon } from '../../StyledComponents'
import { Select } from '../../form/Inputs'
import DataLoader from '../../DataLoader'

const NoWrap = styled.div`
  white-space: nowrap;
`

const BaseFirstSample = React.memo(({ firstFamilySample, compact, hasActiveVariantSample }) => (
  <Sample
    hoverDetails={compact ? 'first loaded' : null}
    isOutdated={!hasActiveVariantSample}
    {...(firstFamilySample || {})}
  />
))

BaseFirstSample.propTypes = {
  firstFamilySample: PropTypes.object,
  compact: PropTypes.bool,
  hasActiveVariantSample: PropTypes.bool,
}

const mapSampleDispatchToProps = (state, ownProps) => ({
  firstFamilySample: (getSamplesByFamily(state)[ownProps.familyGuid] || [])[0],
  hasActiveVariantSample: getHasActiveSearchSampleByFamily(state)[ownProps.familyGuid],
})

export const FirstSample = connect(mapSampleDispatchToProps)(BaseFirstSample)

const BaseAnalystEmailDropdown = React.memo(({ load, loading, onChange, value, ...props }) => (
  <DataLoader load={load} loading={false} content>
    <Select
      loading={loading}
      additionLabel="Assigned Analyst: "
      onChange={onChange}
      value={value}
      placeholder="Unassigned"
      search
      {...props}
    />
  </DataLoader>
))

BaseAnalystEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  onChange: PropTypes.func,
  value: PropTypes.object,
}

const mapDropdownStateToProps = state => ({
  loading: getUserOptionsIsLoading(state),
  options: getUserOptions(state),
})

const mapDropdownDispatchToProps = (dispatch, ownProps) => ({
  load: () => dispatch(loadUserOptions(ownProps.meta.data.formId)),
})

export const AnalystEmailDropdown = connect(
  mapDropdownStateToProps, mapDropdownDispatchToProps,
)(BaseAnalystEmailDropdown)

export const analysisStatusIcon = (
  value, compact, { analysisStatusLastModifiedBy, analysisStatusLastModifiedDate },
) => {
  const icon = <ColoredIcon name="stop" color={value.color} />
  if (!compact && !analysisStatusLastModifiedDate) {
    return icon
  }
  return (
    <Popup
      trigger={icon}
      content={
        <div>
          {compact && value.name}
          {analysisStatusLastModifiedDate && (
            <i>
              {compact && <br />}
              {`Changed on ${new Date(analysisStatusLastModifiedDate).toLocaleDateString()}`}
              <br />
              {`by ${analysisStatusLastModifiedBy}`}
            </i>
          )}
        </div>
      }
      position="top center"
    />
  )
}

const BaseAnalysedBy = React.memo(({ analysedByList, compact, onSubmit }) => {
  const analysedByType = analysedByList.reduce(
    (acc, analysedBy) => ({ ...acc, [analysedBy.dataType]: [...(acc[analysedBy.dataType] || []), analysedBy] }), {},
  )

  if (compact) {
    return [...(analysedByType[SNP_DATA_TYPE] || []).reduce(
      (acc, { createdBy }) => acc.add(createdBy), new Set(),
    )].map(
      analysedByUser => <NoWrap key={analysedByUser}>{analysedByUser}</NoWrap>,
    )
  }

  return FAMILY_ANALYSED_BY_DATA_TYPES.map(([type, typeDisplay]) => (
    <div key={type}>
      <b>{`${typeDisplay}: `}</b>
      {(analysedByType[type] || []).map(
        analysedBy => `${analysedBy.createdBy} (${new Date(analysedBy.lastModifiedDate).toLocaleDateString()})`,
      ).join(', ')}
      &nbsp;&nbsp;
      <DispatchRequestButton
        buttonContent={<Icon link size="small" name="plus" />}
        onSubmit={onSubmit(type)}
        confirmDialog={`Are you sure you want to add that you analysed this family for ${typeDisplay} data?`}
      />
    </div>
  ))
})

BaseAnalysedBy.propTypes = {
  analysedByList: PropTypes.arrayOf(PropTypes.object),
  compact: PropTypes.bool,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: dataType => () => dispatch(
    updateFamily({ dataType, familyGuid: ownProps.familyGuid, familyField: 'analysed_by' }),
  ),
})

export const AnalysedBy = connect(null, mapDispatchToProps)(BaseAnalysedBy)

const BaseAnalysisGroups = React.memo(({ load, loading, ...props }) => (
  <DataLoader load={load} loading={loading} content>
    <TagFieldView {...props} />
  </DataLoader>
))

BaseAnalysisGroups.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapGroupsStateToProps = (state, ownProps) => ({
  fieldValue: getAnalysisGroupsByFamily(state)[ownProps.initialValues.familyGuid],
  loading: getAnalysisGroupIsLoading(state),
  tagOptions: getProjectAnalysisGroupOptions(state)[ownProps.initialValues.projectGuid] || [],
})

const mapGroupsDispatchToProps = (dispatch, ownProps) => ({
  load: () => dispatch(loadProjectAnalysisGroups(ownProps.initialValues.projectGuid)),
})

export const AnalysisGroups = connect(mapGroupsStateToProps, mapGroupsDispatchToProps)(BaseAnalysisGroups)

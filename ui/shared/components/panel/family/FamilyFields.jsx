import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Popup } from 'semantic-ui-react'
import styled from 'styled-components'

import { loadAnalystOptions } from 'redux/rootReducer'
import {
  getSamplesByFamily,
  getUserOptionsIsLoading,
  getHasActiveVariantSampleByFamily,
  getNotesByFamilyType,
} from 'redux/selectors'

import ListFieldView from '../view-fields/ListFieldView'
import Sample from '../sample'
import { ColoredIcon } from '../../StyledComponents'
import { Select } from '../../form/Inputs'
import DataLoader from '../../DataLoader'
import { getAnalystOptions } from '../../../../pages/Project/selectors'

const NoWrap = styled.div`
  white-space: nowrap;
`

const BaseFirstSample = React.memo(({ firstFamilySample, compact, hasActiveVariantSample }) =>
  <Sample
    loadedSample={firstFamilySample}
    hoverDetails={compact ? 'first loaded' : null}
    isOutdated={!hasActiveVariantSample}
  />,
)

BaseFirstSample.propTypes = {
  firstFamilySample: PropTypes.object,
  compact: PropTypes.bool,
  hasActiveVariantSample: PropTypes.bool,
}

const mapSampleDispatchToProps = (state, ownProps) => ({
  firstFamilySample: (getSamplesByFamily(state)[ownProps.familyGuid] || [])[0],
  hasActiveVariantSample: getHasActiveVariantSampleByFamily(state)[ownProps.familyGuid],
})

export const FirstSample = connect(mapSampleDispatchToProps)(BaseFirstSample)

const mapNotesStateToProps = (state, ownProps) => ({
  fieldValue: getNotesByFamilyType(state)[ownProps.initialValues.familyGuid][ownProps.noteType],
})

const NotesFieldView = connect(mapNotesStateToProps)(ListFieldView)

const AnalystEmailDropdown = React.memo(({ load, loading, onChange, value, ...props }) =>
  <DataLoader load={load} loading={false} content>
    <Select
      loading={loading}
      additionLabel="Assigned Analyst: "
      onChange={val => onChange(val)}
      value={value}
      placeholder="Unassigned"
      search
      {...props}
    />
  </DataLoader>,
)

AnalystEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  onChange: PropTypes.func,
  value: PropTypes.any,
}

const mapDropdownStateToProps = state => ({
  loading: getUserOptionsIsLoading(state),
  options: getAnalystOptions(state),
})

const mapDropdownDispatchToProps = {
  load: loadAnalystOptions,
}

AnalystEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  onChange: PropTypes.func,
  value: PropTypes.any,
}

export const ASSIGNED_ANALYST_EDIT_FIELDS = [
  {
    name: 'assigned_analyst_username',
    label: 'Email',
    component: connect(mapDropdownStateToProps, mapDropdownDispatchToProps)(AnalystEmailDropdown),
    width: 16,
    inline: true,
  },
]

export const NOTE_FIELD = {
  canEdit: true,
  component: NotesFieldView,
  itemKey: ({ noteGuid }) => noteGuid,
  itemDisplay: ({ note }) => note, // TODO
}

export const anaysisStatusIcon = (value, compact, { analysisStatusLastModifiedBy, analysisStatusLastModifiedDate }) => {
  const icon = <ColoredIcon name="stop" color={value.color} />
  if (!compact && !analysisStatusLastModifiedDate) {
    return icon
  }
  return (
    <Popup
      trigger={icon}
      content={
        <div>
          {compact && value.text}
          {analysisStatusLastModifiedDate &&
            <i>
              {compact && <br />}Changed on {new Date(analysisStatusLastModifiedDate).toLocaleDateString()}
              <br />by {analysisStatusLastModifiedBy}
            </i>}
        </div>
      }
      position="top center"
    />
  )
}

const formatAnalysedByList = analysedByList =>
  analysedByList.map(analysedBy =>
    `${analysedBy.createdBy.displayName || analysedBy.createdBy.email} (${new Date(analysedBy.lastModifiedDate).toLocaleDateString()})`,
  ).join(', ')

export const AnalysedBy = React.memo(({ analysedByList, compact }) => {
  if (compact) {
    return [...analysedByList.reduce(
      (acc, analysedBy) => acc.add(analysedBy.createdBy.displayName || analysedBy.createdBy.email), new Set(),
    )].map(
      analysedByUser => <NoWrap key={analysedByUser}>{analysedByUser}</NoWrap>,
    )
  }
  const analystUsers = analysedByList.filter(analysedBy => analysedBy.createdBy.isAnalyst)
  const externalUsers = analysedByList.filter(analysedBy => !analysedBy.createdBy.isAnalyst)
  return [
    analystUsers.length > 0 ? <div key="analyst"><b>CMG Analysts:</b> {formatAnalysedByList(analystUsers)}</div> : null,
    externalUsers.length > 0 ? <div key="ext"><b>External Collaborators:</b> {formatAnalysedByList(externalUsers)}</div> : null,
  ]
})

AnalysedBy.propTypes = {
  analysedByList: PropTypes.array,
  compact: PropTypes.bool,
}

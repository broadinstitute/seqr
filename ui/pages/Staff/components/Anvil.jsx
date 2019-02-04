import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import { getProjectsIsLoading, getFamiliesByGuid, getIndividualsByGuid } from 'redux/selectors'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'

// TODO move to shared
import { INDIVIDUAL_EXPORT_DATA } from 'pages/Project/constants'
import { loadProject } from 'pages/Project/reducers'

const RightAligned = styled.span`
  float: right;
`

const COLUMN_CONFIGS = INDIVIDUAL_EXPORT_DATA.concat([]) // TODO variant data

const COLUMNS = COLUMN_CONFIGS.map(({ field, header, format }) => (
  { name: field, content: header, format: format ? row => format(row[field]) : null }
))

// TODO use create selector
const getEntityExportConfig = (rawData, project) => [
  {
    name: 'All Cases',
    data: {
      filename: `anvil_export_${project ? project.name.replace(' ', '_').toLowerCase() : 'all_projects'}`,
      rawData,
      headers: COLUMN_CONFIGS.map(config => config.header),
      processRow: row => COLUMN_CONFIGS.map((config) => {
        const val = row[config.field]
        return config.format ? config.format(val) : val
      }),
    },
  },
]

const getIndividualsWithFamilyId = (familiesByGuid, individualsByGuid) =>
  Object.values(familiesByGuid).reduce((acc, family) =>
    [...acc, ...family.individualGuids.map(individualGuid => (
      { ...individualsByGuid[individualGuid], familyId: family.familyId }
    ))], [],
  )

const Anvil = ({ match, data, loading, load }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <RightAligned>
      <ExportTableButton downloads={getEntityExportConfig(data)} />
      <HorizontalSpacer width={45} />
    </RightAligned>
    <VerticalSpacer height={20} />
    <SortableTable
      striped
      stackable
      collapsing
      idField="individualGuid"
      defaultSortColumn="familyId"
      emptyContent={match.params.projectGuid ? '0 cases found' : 'Select a project to view data'}
      loading={loading}
      data={data}
      columns={COLUMNS}
    />
  </DataLoader>

Anvil.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: getIndividualsWithFamilyId(getFamiliesByGuid(state), getIndividualsByGuid(state)),
  loading: getProjectsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProject,
}

export default connect(mapStateToProps, mapDispatchToProps)(Anvil)

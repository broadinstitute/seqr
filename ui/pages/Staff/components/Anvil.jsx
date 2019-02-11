import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'

import { loadAnvil } from '../reducers'
import { getAnvilLoading, getAnvilRows, getAnvilColumns, getAnvilExportConfig } from '../selectors'

const RightAligned = styled.span`
  float: right;
`

const Anvil = ({ match, data, columns, exportConfig, loading, load }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <RightAligned>
      <ExportTableButton downloads={exportConfig} />
      <HorizontalSpacer width={45} />
    </RightAligned>
    <VerticalSpacer height={20} />
    <SortableTable
      striped
      collapsing
      idField="individualGuid"
      defaultSortColumn="familyId"
      emptyContent={match.params.projectGuid ? '0 cases found' : 'Select a project to view data'}
      loading={loading}
      data={data}
      columns={columns}
    />
  </DataLoader>

Anvil.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  columns: PropTypes.array,
  exportConfig: PropTypes.array,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  data: getAnvilRows(state),
  columns: getAnvilColumns(state),
  exportConfig: getAnvilExportConfig(state, ownProps),
  loading: getAnvilLoading(state),
})

const mapDispatchToProps = {
  load: loadAnvil,
}

export default connect(mapStateToProps, mapDispatchToProps)(Anvil)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'

import { loadAnvil } from '../reducers'
import { getAnvilLoading, getAnvilRows, getAnvilColumns, getAnvilExportConfig } from '../selectors'

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const RightAligned = styled.span`
  float: right;
`

const AwesomebarContainer = styled.div`
  display: inline-block;
`

const getResultHref = result => `/staff/anvil/${result.key}`

const Anvil = ({ match, data, columns, exportConfig, loading, load }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <AwesomebarContainer>
      <AwesomeBar
        categories={SEARCH_CATEGORIES}
        placeholder="Enter project name"
        inputwidth="400px"
        getResultHref={getResultHref}
      />
    </AwesomebarContainer>
    or <NavLink to="/staff/anvil/all" activeStyle={ACTIVE_LINK_STYLE}>view all AnVIL projects</NavLink>
    <RightAligned>
      <ExportTableButton downloads={exportConfig} />
      <HorizontalSpacer width={45} />
    </RightAligned>
    <VerticalSpacer height={20} />
    <SortableTable
      striped
      collapsing
      horizontalScroll
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

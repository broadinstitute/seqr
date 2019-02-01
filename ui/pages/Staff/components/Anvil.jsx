import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import { getProjectsIsLoading } from 'redux/selectors'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { InlineHeader } from 'shared/components/StyledComponents'

// TODO move to shared
import {
  INDIVIDUAL_FIELDS, INDIVIDUAL_NOTES_CONFIG, INDIVIDUAL_HPO_EXPORT_DATA, INDIVIDUAL_EXPORT_DATA,
} from 'pages/Project/constants'
import { loadProject } from 'pages/Project/reducers'

const RightAligned = styled.span`
  float: right;
`

const COLUMNS = INDIVIDUAL_FIELDS.concat(
  [INDIVIDUAL_NOTES_CONFIG, { name: 'codedPhenotype', content: 'Phenotype' }],
  INDIVIDUAL_HPO_EXPORT_DATA.map(({ field, header, format }) => (
    { name: header, content: header, format: row => format(row[field]) }
  )),
  // TODO variant data
).map(({ width, ...col }) => ({ width: 1, ...col }))


const ANVIL_DOWNLOADS = INDIVIDUAL_EXPORT_DATA.concat(
  [],
  // TODO variant data
)

const Anvil = ({ projectGuid, data, loading, load }) =>
  <DataLoader contentId={projectGuid} load={load} content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <RightAligned>
      <ExportTableButton downloads={ANVIL_DOWNLOADS} />
      <HorizontalSpacer width={45} />
    </RightAligned>
    <VerticalSpacer height={10} />
    <SortableTable
      striped
      stackable
      fixed
      idField="individualGuid"
      defaultSortColumn="familyId"
      emptyContent={projectGuid ? '0 projects found' : 'Select a project to view data'}
      loading={loading}
      data={data}
      columns={COLUMNS}
    />
  </DataLoader>

Anvil.propTypes = {
  projectGuid: PropTypes.string,
  data: PropTypes.array,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: [],
  loading: getProjectsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProject,
}

export default connect(mapStateToProps, mapDispatchToProps)(Anvil)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Popup, Visibility } from 'semantic-ui-react'
import { connect } from 'react-redux'

import DataLoader from 'shared/components/DataLoader'
import { ExportTableButtonContent, DownloadButton } from 'shared/components/buttons/ExportTableButton'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import TableLoading from 'shared/components/table/TableLoading'
import { HorizontalSpacer } from 'shared/components/Spacers'

import {
  getVisibleFamiliesInSortedOrder, getFamiliesLoading, getProjectOverviewIsLoading, getProjectExportUrls,
  getIndivdualsLoading,
} from '../../selectors'
import { loadFamilies, loadProjectExportData } from '../../reducers'
import { FamilyDetail } from '../FamilyPage'
import CollapsableLayout from './CollapsableLayout'
import TableHeaderRow from './header/TableHeaderRow'

const ExportContainer = styled.span`
  float: right;
  padding-bottom: 15px;
`

const EmptyCell = styled(Table.Cell)`
  padding: 10px 0px 10px 15px;
  color: gray;
  border-width: 0px;
`

// Allows dropdowns to be visible inside table cell
const OverflowCell = styled(Table.Cell)`
  overflow: visible !important;
  
  td {
    overflow: visible !important;
  }
`

class FamilyTableRow extends React.PureComponent {

  static propTypes = {
    familyGuid: PropTypes.string.isRequired,
    tableName: PropTypes.string,
    detailFields: PropTypes.arrayOf(PropTypes.object),
    noDetailFields: PropTypes.arrayOf(PropTypes.object),
    showVariantDetails: PropTypes.bool,
  }

  state = { isVisible: false }

  handleOnScreen = () => {
    this.setState({ isVisible: true })
  }

  render() {
    const { isVisible } = this.state

    return (
      <Table.Row>
        <OverflowCell width={16}>
          <Visibility fireOnMount onOnScreen={this.handleOnScreen}>
            {isVisible && <CollapsableLayout layoutComponent={FamilyDetail} showFamilyPageLink {...this.props} />}
          </Visibility>
        </OverflowCell>
      </Table.Row>
    )
  }

}

const BaseFamilyTableRows = ({ visibleFamilies, ...props }) => (
  visibleFamilies.length > 0 ? visibleFamilies.map(family => (
    <FamilyTableRow
      key={family.familyGuid}
      familyGuid={family.familyGuid}
      {...props}
    />
  )) : (
    <Table.Row>
      <EmptyCell content="0 families found" />
    </Table.Row>
  )
)

const mapFamilyRowsStateToProps = (state, ownProps) => ({
  visibleFamilies: getVisibleFamiliesInSortedOrder(state, ownProps),
})

BaseFamilyTableRows.propTypes = {
  visibleFamilies: PropTypes.arrayOf(PropTypes.object).isRequired,
}

const FamilyTableRows = connect(mapFamilyRowsStateToProps)(BaseFamilyTableRows)

const FamilyTable = React.memo(({
  load, loading, headerStatus, exportUrls, noDetailFields, tableName, showVariantDetails,
  loadExportData, exportDataLoading, ...props
}) => (
  <DataLoader load={load} loading={false} content>
    <ExportContainer>
      {headerStatus && (
        <span>
          {`${headerStatus.title}:  `}
          <HorizontalStackedBar
            width={100}
            height={14}
            title={headerStatus.title}
            data={headerStatus.data}
          />
          <HorizontalSpacer width={10} />
        </span>
      )}
      <Popup
        trigger={<DownloadButton />}
        content={
          <DataLoader load={loadExportData} loading={exportDataLoading} content>
            <ExportTableButtonContent downloads={exportUrls} />
          </DataLoader>
        }
        on="click"
        position="bottom center"
      />
      <HorizontalSpacer width={45} />
    </ExportContainer>
    <Table compact fixed attached="top">
      <TableHeaderRow
        fields={noDetailFields}
        tableName={tableName}
        showVariantDetails={showVariantDetails}
        analysisGroupGuid={props.analysisGroupGuid}
      />
    </Table>
    <Table striped compact fixed attached="bottom">
      <Table.Body>
        {loading && <TableLoading />}
        {!loading && (
          <FamilyTableRows
            noDetailFields={noDetailFields}
            showVariantDetails={showVariantDetails}
            tableName={tableName}
            {...props}
          />
        )}
      </Table.Body>
      <Table.Footer>
        <Table.Row>
          <Table.HeaderCell />
          <Table.HeaderCell />
        </Table.Row>
      </Table.Footer>
    </Table>
  </DataLoader>
))

export { FamilyTable as FamilyTableComponent }

FamilyTable.propTypes = {
  loading: PropTypes.bool,
  load: PropTypes.func,
  exportDataLoading: PropTypes.bool,
  loadExportData: PropTypes.func,
  headerStatus: PropTypes.object,
  exportUrls: PropTypes.arrayOf(PropTypes.object),
  showVariantDetails: PropTypes.bool,
  noDetailFields: PropTypes.arrayOf(PropTypes.object),
  tableName: PropTypes.string,
  analysisGroupGuid: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  loading: getFamiliesLoading(state) || getProjectOverviewIsLoading(state),
  exportDataLoading: getFamiliesLoading(state) || getIndivdualsLoading(state),
  exportUrls: getProjectExportUrls(state, ownProps),
})

const mapDispatchToProps = {
  load: loadFamilies,
  loadExportData: loadProjectExportData,
}

export default connect(mapStateToProps, mapDispatchToProps)(FamilyTable)

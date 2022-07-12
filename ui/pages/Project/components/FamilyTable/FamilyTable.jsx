import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Icon, Popup, Visibility } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

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
import TableHeaderRow from './header/TableHeaderRow'

const ExportContainer = styled.span`
  float: right;
  padding-bottom: 15px;
`

const ToggleIcon = styled(Icon).attrs({ size: 'large', link: true, name: 'dropdown' })`
  position: relative;
  z-index: 1;
`

const EmptyCell = styled(Table.Cell)`
  padding: 10px 0px 10px 15px;
  color: gray;
  border-width: 0px;
`

// Allows dropdowns to be visible inside table cell
const OverflowCell = styled(Table.Cell)`
  overflow: visible !important;
`

class FamilyTableRow extends React.PureComponent {

  static propTypes = {
    familyGuid: PropTypes.string.isRequired,
    tableName: PropTypes.string,
    detailFields: PropTypes.arrayOf(PropTypes.object),
    noDetailFields: PropTypes.arrayOf(PropTypes.object),
    showVariantDetails: PropTypes.bool,
    showDetails: PropTypes.bool,
  }

  state = { showDetails: null, isVisible: false }

  toggle = () => {
    const { showDetails } = this.props
    this.setState(prevState => (
      { showDetails: !(prevState.showDetails === null ? showDetails : prevState.showDetails) }
    ))
  }

  handleOnScreen = () => {
    this.setState({ isVisible: true })
  }

  render() {
    const {
      familyGuid, showVariantDetails, detailFields, noDetailFields, tableName, showDetails: initialShowDetails,
    } = this.props
    const { showDetails, isVisible } = this.state
    const showFamilyDetails = showDetails === null ? initialShowDetails : showDetails
    return (
      <Table.Row>
        <Table.Cell collapsing verticalAlign="top">
          {detailFields && noDetailFields &&
            <ToggleIcon rotated={showFamilyDetails ? undefined : 'counterclockwise'} onClick={this.toggle} />}
        </Table.Cell>
        <OverflowCell>
          <Visibility fireOnMount onOnScreen={this.handleOnScreen}>
            {isVisible && (
              <FamilyDetail
                key={familyGuid}
                familyGuid={familyGuid}
                showFamilyPageLink
                showVariantDetails={showVariantDetails}
                tableName={tableName}
                fields={showFamilyDetails ? detailFields : noDetailFields}
                compact={!showFamilyDetails}
                disableEdit={!showFamilyDetails}
              />
            )}
          </Visibility>
        </OverflowCell>
      </Table.Row>
    )
  }

}

const FamilyTable = React.memo(({
  visibleFamilies, load, loading, headerStatus, exportUrls, noDetailFields, tableName, showVariantDetails,
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
        analysisGroupGuid={props.match.params.analysisGroupGuid}
      />
    </Table>
    <Table striped compact attached="bottom">
      <Table.Body>
        {loading && <TableLoading />}
        {!loading && (visibleFamilies.length > 0 ? visibleFamilies.map(family => (
          <FamilyTableRow
            key={family.familyGuid}
            familyGuid={family.familyGuid}
            noDetailFields={noDetailFields}
            showVariantDetails={showVariantDetails}
            tableName={tableName}
            {...props}
          />
        )) : (
          <Table.Row>
            <EmptyCell content="0 families found" />
          </Table.Row>
        ))}
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
  visibleFamilies: PropTypes.arrayOf(PropTypes.object).isRequired,
  loading: PropTypes.bool,
  load: PropTypes.func,
  exportDataLoading: PropTypes.bool,
  loadExportData: PropTypes.func,
  headerStatus: PropTypes.object,
  exportUrls: PropTypes.arrayOf(PropTypes.object),
  showVariantDetails: PropTypes.bool,
  noDetailFields: PropTypes.arrayOf(PropTypes.object),
  tableName: PropTypes.string,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamilies: getVisibleFamiliesInSortedOrder(state, ownProps),
  loading: getFamiliesLoading(state) || getProjectOverviewIsLoading(state),
  exportDataLoading: getFamiliesLoading(state) || getIndivdualsLoading(state),
  exportUrls: getProjectExportUrls(state, ownProps),
})

const mapDispatchToProps = {
  load: loadFamilies,
  loadExportData: loadProjectExportData,
}

export default withRouter(connect(mapStateToProps, mapDispatchToProps)(FamilyTable))

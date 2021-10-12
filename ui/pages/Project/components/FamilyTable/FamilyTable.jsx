import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

import ExportTableButton from 'shared/components/buttons/ExportTableButton'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import TableLoading from 'shared/components/table/TableLoading'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { getVisibleFamiliesInSortedOrder, getProjectDetailsIsLoading, getProjectExportUrls } from '../../selectors'
import { FamilyDetail } from '../FamilyPage'
import TableHeaderRow from './header/TableHeaderRow'
import EmptyTableRow from './EmptyTableRow'

const ExportContainer = styled.span`
  float: right;
  padding-bottom: 15px;
`

const ToggleIcon = styled(Icon).attrs({ size: 'large', link: true, name: 'dropdown' })`
  position: relative;
  z-index: 1;
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

  state = { showDetails: null }

  toggle = () => {
    const { showDetails } = this.props
    this.setState(prevState => (
      { showDetails: !(prevState.showDetails === null ? showDetails : prevState.showDetails) }
    ))
  }

  render() {
    const {
      familyGuid, showVariantDetails, detailFields, noDetailFields, tableName, showDetails: initialShowDetails,
    } = this.props
    const { showDetails } = this.state
    const showFamilyDetails = showDetails === null ? initialShowDetails : showDetails
    return (
      <Table.Row>
        <OverflowCell>
          <FamilyDetail
            key={familyGuid}
            familyGuid={familyGuid}
            showFamilyPageLink
            showVariantDetails={showVariantDetails}
            tableName={tableName}
            fields={showFamilyDetails ? detailFields : noDetailFields}
            compact={!showFamilyDetails}
            disableEdit={!showFamilyDetails}
            annotation={detailFields && noDetailFields && <ToggleIcon rotated={showFamilyDetails ? undefined : 'counterclockwise'} onClick={this.toggle} />}
            showIndividuals={showFamilyDetails}
          />
        </OverflowCell>
      </Table.Row>
    )
  }

}

const FamilyTable = React.memo((
  { visibleFamilies, loading, headerStatus, exportUrls, noDetailFields, tableName, showVariantDetails, ...props },
) => (
  <div>
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
      <ExportTableButton downloads={exportUrls} />
      <HorizontalSpacer width={45} />
    </ExportContainer>
    <Table padded fixed attached="top">
      <TableHeaderRow
        fields={noDetailFields}
        tableName={tableName}
        showVariantDetails={showVariantDetails}
        analysisGroupGuid={props.match.params.analysisGroupGuid}
      />
    </Table>
    <Table celled striped padded fixed attached="bottom">
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
        )) : <EmptyTableRow tableName={tableName} />)}
      </Table.Body>
      <Table.Footer><Table.Row><Table.HeaderCell /></Table.Row></Table.Footer>
    </Table>
  </div>
))

export { FamilyTable as FamilyTableComponent }

FamilyTable.propTypes = {
  visibleFamilies: PropTypes.arrayOf(PropTypes.object).isRequired,
  loading: PropTypes.bool,
  headerStatus: PropTypes.object,
  exportUrls: PropTypes.arrayOf(PropTypes.object),
  showVariantDetails: PropTypes.bool,
  noDetailFields: PropTypes.arrayOf(PropTypes.object),
  tableName: PropTypes.string,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamilies: getVisibleFamiliesInSortedOrder(state, ownProps),
  loading: getProjectDetailsIsLoading(state),
  exportUrls: getProjectExportUrls(state, ownProps),
})

export default withRouter(connect(mapStateToProps)(FamilyTable))

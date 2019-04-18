import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import TableLoading from 'shared/components/table/TableLoading'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { getVisibleFamiliesInSortedOrder, getProjectDetailsIsLoading } from '../../selectors'
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

  constructor(props) {
    super(props)

    this.state = {
      showDetails: props.showDetails,
    }
  }

  toggle = () => {
    this.setState({ showDetails: !this.state.showDetails })
  }

  render() {
    const { familyGuid, editCaseReview, showVariantDetails, detailFields, noDetailFields } = this.props
    return (
      <Table.Row>
        <OverflowCell>
          <FamilyDetail
            key={familyGuid}
            familyGuid={familyGuid}
            showFamilyPageLink
            showVariantDetails={showVariantDetails}
            fields={this.state.showDetails ? detailFields : noDetailFields}
            compact={!this.state.showDetails}
            annotation={detailFields && noDetailFields && <ToggleIcon rotated={this.state.showDetails ? undefined : 'counterclockwise'} onClick={this.toggle} />}
            showIndividuals={this.state.showDetails}
            editCaseReview={editCaseReview}
          />
        </OverflowCell>
      </Table.Row>
    )
  }
}

FamilyTableRow.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  editCaseReview: PropTypes.bool,
  detailFields: PropTypes.array,
  noDetailFields: PropTypes.array,
  showVariantDetails: PropTypes.bool,
  showDetails: PropTypes.bool,
}

const FamilyTable = ({ visibleFamilies, loading, headerStatus, showInternalFilters, exportUrls, noDetailFields, tableName, showVariantDetails, ...props }) =>
  <div>
    <ExportContainer>
      {headerStatus &&
        <span>
          {headerStatus.title}:
          <HorizontalSpacer width={10} />
          <HorizontalStackedBar
            width={100}
            height={14}
            title={headerStatus.title}
            data={headerStatus.data}
          />
          <HorizontalSpacer width={10} />
        </span>
      }
      <ExportTableButton downloads={exportUrls} />
      <HorizontalSpacer width={45} />
    </ExportContainer>
    <Table padded fixed attached="top">
      <TableHeaderRow
        showInternalFilters={showInternalFilters}
        fields={noDetailFields}
        tableName={tableName}
        showVariantDetails={showVariantDetails}
        analysisGroupGuid={props.match.params.analysisGroupGuid}
      />
    </Table>
    <Table celled striped padded fixed attached="bottom">
      <Table.Body>
        {loading && <TableLoading />}
        {!loading && (visibleFamilies.length > 0 ?
          visibleFamilies.map(family =>
            <FamilyTableRow
              key={family.familyGuid}
              familyGuid={family.familyGuid}
              noDetailFields={noDetailFields}
              showVariantDetails={showVariantDetails}
              {...props}
            />,
          ) : <EmptyTableRow tableName={tableName} />)
        }
      </Table.Body>
      <Table.Footer><Table.Row><Table.HeaderCell /></Table.Row></Table.Footer>
    </Table>
  </div>


export { FamilyTable as FamilyTableComponent }

FamilyTable.propTypes = {
  visibleFamilies: PropTypes.array.isRequired,
  loading: PropTypes.bool,
  headerStatus: PropTypes.object,
  showInternalFilters: PropTypes.bool,
  editCaseReview: PropTypes.bool,
  exportUrls: PropTypes.array,
  showVariantDetails: PropTypes.bool,
  noDetailFields: PropTypes.array,
  tableName: PropTypes.string,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamilies: getVisibleFamiliesInSortedOrder(state, ownProps),
  loading: getProjectDetailsIsLoading(state),
})

export default withRouter(connect(mapStateToProps)(FamilyTable))

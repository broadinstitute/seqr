import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import TableLoading from 'shared/components/table/TableLoading'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { getVisibleSortedFamiliesWithIndividuals, getProjectDetailsIsLoading } from '../../selectors'
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
    const { family, editCaseReview, showSearchLinks, showVariantTags, detailFields, noDetailFields } = this.props
    return (
      <Table.Row>
        <Table.Cell>
          <FamilyDetail
            key={family.familyGuid}
            family={family}
            showFamilyPageLink
            showSearchLinks={this.state.showDetails && showSearchLinks}
            showVariantTags={showVariantTags}
            fields={this.state.showDetails ? detailFields : noDetailFields}
            compact={!this.state.showDetails}
            annotation={detailFields && noDetailFields && <ToggleIcon rotated={this.state.showDetails ? undefined : 'counterclockwise'} onClick={this.toggle} />}
            individuals={this.state.showDetails && family.individuals}
            editCaseReview={editCaseReview}
          />
        </Table.Cell>
      </Table.Row>
    )
  }
}

FamilyTableRow.propTypes = {
  family: PropTypes.object.isRequired,
  editCaseReview: PropTypes.bool,
  detailFields: PropTypes.array,
  noDetailFields: PropTypes.array,
  showSearchLinks: PropTypes.bool,
  showVariantTags: PropTypes.bool,
  showDetails: PropTypes.bool,
}

const FamilyTable = ({ visibleFamilies, loading, headerStatus, showInternalFilters, exportUrls, noDetailFields, tableName, showVariantTags, ...props }) =>
  <div>
    <ExportContainer>
      <ExportTableButton downloads={exportUrls} />
      <HorizontalSpacer width={45} />
    </ExportContainer>
    <Table attached="top">
      <TableHeaderRow
        headerStatus={headerStatus}
        showInternalFilters={showInternalFilters}
        fields={noDetailFields}
        tableName={tableName}
        showVariantTags={showVariantTags}
      />
    </Table>
    <Table celled striped padded fixed attached="bottom">
      <Table.Body>
        {loading && <TableLoading />}
        {!loading && (visibleFamilies.length > 0 ?
          visibleFamilies.map(family =>
            <FamilyTableRow
              key={family.familyGuid}
              family={family}
              noDetailFields={noDetailFields}
              showVariantTags={showVariantTags}
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
  showSearchLinks: PropTypes.bool,
  showVariantTags: PropTypes.bool,
  noDetailFields: PropTypes.array,
  tableName: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamilies: getVisibleSortedFamiliesWithIndividuals(state, ownProps),
  loading: getProjectDetailsIsLoading(state),
})

export default withRouter(connect(mapStateToProps)(FamilyTable))

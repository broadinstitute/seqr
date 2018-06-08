import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

import Family from 'shared/components/panel/family'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ButtonLink from 'shared/components/buttons/ButtonLink'
import TableLoading from 'shared/components/table/TableLoading'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'

import { getVisibleSortedFamiliesWithIndividuals, getProjectDetailsIsLoading, getShowDetails } from '../../selectors'
import TableHeaderRow from './header/TableHeaderRow'
import EmptyTableRow from './EmptyTableRow'
import IndividualRow from './IndividualRow'
import PageSelector from './PageSelector'


const ExportContainer = styled.span`
  float: right;
  padding-top: 15px;
`

class FamilyTableRow extends React.PureComponent {

  constructor(props) {
    super(props)

    this.state = {
      showDetails: props.showDetails,
    }
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.showDetails !== this.props.showDetails) {
      this.setState({ showDetails: nextProps.showDetails })
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
          <Family
            key={family.familyGuid}
            family={family}
            showSearchLinks={this.state.showDetails && showSearchLinks}
            showVariantTags={showVariantTags}
            fields={this.state.showDetails ? detailFields : noDetailFields}
            compact={!this.state.showDetails}
          />
          {this.state.showDetails && family.individuals.map(individual => (
            <IndividualRow
              key={individual.individualGuid}
              family={family}
              individual={individual}
              editCaseReview={editCaseReview}
            />),
          )}
          <VerticalSpacer height={10} />
          <ButtonLink onClick={this.toggle}>
            <Icon name={`angle double ${this.state.showDetails ? 'up' : 'down'}`} />
            Show {this.state.showDetails ? 'Less' : 'More'}
          </ButtonLink>
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

const FamilyTable = ({ visibleFamilies, loading, headerStatus, showInternalFilters, exportUrls, ...props }) =>
  <div>
    <PageSelector />
    <ExportContainer>
      <ExportTableButton downloads={exportUrls} />
      <HorizontalSpacer width={45} />
    </ExportContainer>
    <Table celled striped padded>
      <TableHeaderRow headerStatus={headerStatus} showInternalFilters={showInternalFilters} />
      <Table.Body>
        {loading ? <TableLoading /> : null}
        {
          !loading && visibleFamilies.length > 0 ?
            visibleFamilies.map(family => <FamilyTableRow key={family.familyGuid}family={family} {...props} />)
            : <EmptyTableRow />
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
  showDetails: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamilies: getVisibleSortedFamiliesWithIndividuals(state, ownProps),
  showDetails: getShowDetails(state),
  loading: getProjectDetailsIsLoading(state),
})

export default withRouter(connect(mapStateToProps)(FamilyTable))

import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { projectDetailsLoading } from 'redux/rootReducer'
import TableLoading from 'shared/components/table/TableLoading'
import TableHeaderRow from './header/TableHeaderRow'
import TableFooterRow from './TableFooterRow'
import EmptyTableRow from './EmptyTableRow'
import FamilyRow from './FamilyRow'
import IndividualRow from './IndividualRow'
import { getVisibleSortedFamiliesWithIndividuals } from '../../utils/visibleFamiliesSelector'

const FamilyTable = props =>
  <Table celled style={{ width: '100%' }}>
    <Table.Body>
      <TableHeaderRow />
      {props.loading ? <TableLoading /> : null}
      {
        !props.loading && props.visibleFamilies.length > 0 ?
          props.visibleFamilies.map((family, i) =>
            <Table.Row key={family.familyGuid} style={{ backgroundColor: (i % 2 === 0) ? 'white' : '#F3F3F3' }}>
              <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
                {[
                  <FamilyRow key={family.familyGuid} family={family} />,
                  family.individuals.map(individual => (
                    <IndividualRow key={individual.individualGuid} family={family} individual={individual} />),
                  ),
                ]}
              </Table.Cell>
            </Table.Row>)
          : <EmptyTableRow />
      }
      <TableFooterRow />
    </Table.Body>
  </Table>

export { FamilyTable as FamilyTableComponent }

FamilyTable.propTypes = {
  visibleFamilies: PropTypes.array.isRequired,
  loading: PropTypes.bool,
}

const mapStateToProps = state => ({
  visibleFamilies: getVisibleSortedFamiliesWithIndividuals(state),
  loading: projectDetailsLoading(state),

})

export default connect(mapStateToProps)(FamilyTable)

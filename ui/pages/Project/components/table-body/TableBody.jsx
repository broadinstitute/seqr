import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'

import TableHeaderRow from '../table-header/TableHeaderRow'
import TableFooterRow from '../table-footer/TableFooterRow'
import EmptyTableRow from './EmptyTableRow'
import FamilyRow from './family/FamilyRow'
import IndividualRow from './individual/IndividualRow'

import { getVisibleFamiliesInSortedOrder, getFamilyGuidToIndividuals } from '../../utils/visibleFamiliesSelector'

const TableBody = props =>
  <Table.Body>
    <TableHeaderRow />
    {
      props.visibleFamilies.length > 0 ?
        props.visibleFamilies.map((family, i) =>
          <Table.Row key={family.familyGuid} style={{ backgroundColor: (i % 2 === 0) ? 'white' : '#F3F3F3' }}>
            <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
              {[
                <FamilyRow key={family.familyGuid} family={family} />,
                ...props.familyGuidToIndividuals[family.familyGuid].map(individual => (
                  <IndividualRow key={individual.individualGuid} family={family} individual={individual} />),
                ),
              ]}
            </Table.Cell>
          </Table.Row>)
        : <EmptyTableRow />
    }
    <TableFooterRow />
  </Table.Body>

export { TableBody as TableBodyComponent }

TableBody.propTypes = {
  visibleFamilies: PropTypes.array.isRequired,
  familyGuidToIndividuals: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  visibleFamilies: getVisibleFamiliesInSortedOrder(state),
  familyGuidToIndividuals: getFamilyGuidToIndividuals(state),
})

export default connect(mapStateToProps)(TableBody)

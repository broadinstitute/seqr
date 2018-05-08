import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getProjectDetailsIsLoading } from 'redux/rootReducer'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import TableLoading from 'shared/components/table/TableLoading'
import TableHeaderRow from './header/TableHeaderRow'
import TableFooterRow from './TableFooterRow'
import EmptyTableRow from './EmptyTableRow'
import FamilyRow from './FamilyRow'
import IndividualRow from './IndividualRow'
import PageSelector from './PageSelector'
import { getVisibleSortedFamiliesWithIndividuals } from '../../utils/selectors'

const FamilyTable = ({ visibleFamilies, loading, headerStatus, showInternalFields, editCaseReview, exportUrls }) =>
  <div>
    <div style={{ padding: '0px 65px 10px 0px' }}>
      <PageSelector />
      <div style={{ float: 'right' }}>
        <ExportTableButton urls={exportUrls} />
      </div>
    </div>
    <Table celled style={{ width: '100%' }}>
      <TableHeaderRow headerStatus={headerStatus} showInternalFilters={showInternalFields} />
      <Table.Body>
        {loading ? <TableLoading /> : null}
        {
          !loading && visibleFamilies.length > 0 ?
            visibleFamilies.map((family, i) =>
              <Table.Row key={family.familyGuid} style={{ backgroundColor: (i % 2 === 0) ? 'white' : '#F3F3F3' }}>
                <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
                  {[
                    <FamilyRow key={family.familyGuid} family={family} showInternalFields={showInternalFields} />,
                    family.individuals.map(individual => (
                      <IndividualRow
                        key={individual.individualGuid}
                        family={family}
                        individual={individual}
                        editCaseReview={editCaseReview}
                      />),
                    ),
                  ]}
                </Table.Cell>
              </Table.Row>)
            : <EmptyTableRow />
        }
        <TableFooterRow />
      </Table.Body>
    </Table>
  </div>


export { FamilyTable as FamilyTableComponent }

FamilyTable.propTypes = {
  visibleFamilies: PropTypes.array.isRequired,
  loading: PropTypes.bool,
  headerStatus: PropTypes.object,
  showInternalFields: PropTypes.bool,
  editCaseReview: PropTypes.bool,
  exportUrls: PropTypes.array,
}

const mapStateToProps = state => ({
  visibleFamilies: getVisibleSortedFamiliesWithIndividuals(state),
  loading: getProjectDetailsIsLoading(state),

})

export default connect(mapStateToProps)(FamilyTable)

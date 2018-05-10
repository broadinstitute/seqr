import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { connect } from 'react-redux'

import Family from 'shared/components/panel/family'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import TableLoading from 'shared/components/table/TableLoading'

import { getVisibleSortedFamiliesWithIndividuals, getProjectDetailsIsLoading } from '../../selectors'
import TableHeaderRow from './header/TableHeaderRow'
import TableFooterRow from './TableFooterRow'
import EmptyTableRow from './EmptyTableRow'
import IndividualRow from './IndividualRow'
import PageSelector from './PageSelector'


const FamilyTable = ({ visibleFamilies, loading, headerStatus, showSearchLinks, fields, showInternalFilters, editCaseReview, exportUrls }) =>
  <div>
    <div style={{ padding: '0px 65px 10px 0px' }}>
      <PageSelector />
      <div style={{ float: 'right' }}>
        <ExportTableButton urls={exportUrls} />
      </div>
    </div>
    <Table celled style={{ width: '100%' }}>
      <TableHeaderRow headerStatus={headerStatus} showInternalFilters={showInternalFilters} />
      <Table.Body>
        {loading ? <TableLoading /> : null}
        {
          !loading && visibleFamilies.length > 0 ?
            visibleFamilies.map((family, i) =>
              <Table.Row key={family.familyGuid} style={{ backgroundColor: (i % 2 === 0) ? 'white' : '#F3F3F3' }}>
                <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
                  {[
                    <Family
                      key={family.familyGuid}
                      family={family}
                      showSearchLinks={showSearchLinks}
                      fields={fields}
                    />,
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
  showInternalFilters: PropTypes.bool,
  editCaseReview: PropTypes.bool,
  exportUrls: PropTypes.array,
  fields: PropTypes.array,
  showSearchLinks: PropTypes.bool,
}

const mapStateToProps = state => ({
  visibleFamilies: getVisibleSortedFamiliesWithIndividuals(state),
  loading: getProjectDetailsIsLoading(state),
})

export default connect(mapStateToProps)(FamilyTable)

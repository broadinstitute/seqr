import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'

import DataLoader from 'shared/components/DataLoader'
import SearchResultsLink from 'shared/components/buttons/SearchResultsLink'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import Modal from 'shared/components/modal/Modal'
import SortableTable from 'shared/components/table/SortableTable'
import { ButtonLink } from 'shared/components/StyledComponents'

import {
  getSearchGeneBreakdownValues,
  getSearchGeneBreakdownLoading,
  getSearchGeneBreakdownErrorMessage,
} from '../selectors'
import { loadGeneBreakdown } from '../reducers'

// TODO download
const COLUMNS = [
  {
    name: 'geneSymbol',
    content: 'Gene',
    width: 3,
    format: row => <ShowGeneModal gene={row} />, // TODO constraint/omim labels
  },
  {
    name: 'numVariants',
    content: '# Variants',
    width: 3,
    format: row =>
      // TODO should only link to searched variants, not all in gene
      <span>
        {row.numVariants} (<SearchResultsLink geneId={row.geneId} familyGuids={row.families.map(({ family }) => family.familyGuid)} />)
      </span>,
  },
  { name: 'numFamilies', content: '# Families', width: 2 },
  {
    name: 'families',
    content: 'Families',
    width: 8,
    // TODO hover family id for detail
    format: row => row.families.map(({ family, count }) => `${family.familyId} (${count})`).join(', '),
  },
]

const GeneBreakdown = ({ searchHash, geneBreakdown, loading, loadingErrorMessage, load }) =>
  <Modal
    modalName="geneBreakdown"
    title={`${loading ? '' : `${geneBreakdown.length} `}Genes from Search Results`}
    trigger={<ButtonLink content="View Gene Breakdown" icon="search" />}
  >
    <DataLoader contentId={searchHash} load={load} loading={false} content>
      <SortableTable
        idField="geneId"
        defaultSortColumn="geneSymbol"
        loading={loading}
        emptyContent={loadingErrorMessage}
        data={geneBreakdown}
        columns={COLUMNS}
        fixedWidth
      />
    </DataLoader>
  </Modal>

GeneBreakdown.propTypes = {
  searchHash: PropTypes.string,
  geneBreakdown: PropTypes.array,
  loading: PropTypes.bool,
  loadingErrorMessage: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  geneBreakdown: getSearchGeneBreakdownValues(state, ownProps),
  loading: getSearchGeneBreakdownLoading(state),
  loadingErrorMessage: getSearchGeneBreakdownErrorMessage(state),
})

const mapDispatchToProps = {
  load: loadGeneBreakdown,
}

export default connect(mapStateToProps, mapDispatchToProps)(GeneBreakdown)

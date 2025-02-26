import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'

import DataLoader from 'shared/components/DataLoader'
import FamilyLink from 'shared/components/buttons/FamilyLink'
import SearchResultsLink from 'shared/components/buttons/SearchResultsLink'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import Modal from 'shared/components/modal/Modal'
import { GeneDetails } from 'shared/components/panel/variants/VariantGene'
import DataTable from 'shared/components/table/DataTable'
import { ButtonLink } from 'shared/components/StyledComponents'

import {
  getSearchGeneBreakdownValues,
  getSearchGeneBreakdownLoading,
  getSearchGeneBreakdownErrorMessage,
} from '../selectors'
import { loadGeneBreakdown } from '../reducers'

const COLUMNS = [
  {
    name: 'geneSymbol',
    content: 'Gene',
    width: 4,
    noFormatExport: true,
    format: row => (
      <div>
        <ShowGeneModal gene={row} size="large" />
        <GeneDetails gene={row} margin="0.5em 0.5em 0 0" />
      </div>
    ),
  },
  {
    name: 'numVariants',
    content: '# Variants',
    width: 2,
    noFormatExport: true,
    format: row => (
      <SearchResultsLink
        location={row.geneId}
        familyGuids={row.families.map(({ family }) => family.familyGuid)}
        buttonText={row.numVariants.toString()}
        initialSearch={row.search}
      />
    ),
  },
  { name: 'numFamilies', content: '# Families', width: 2, noFormatExport: true },
  {
    name: 'families',
    content: 'Families',
    width: 8,
    format: (row, isExport) => (
      isExport ? row.families.map(({ family, count }) => `${family.displayName} (${count})`).join(', ') :
        row.families.map(({ family, count }, index) => (
          <span key={family.familyGuid}>
            {index > 0 && <span>,&nbsp;</span>}
            <FamilyLink family={family} target="_blank" disableEdit />
            {`(${count})`}
          </span>
        ))
    ),
  },
]

const GeneBreakdown = React.memo(({ searchHash, geneBreakdown, loading, loadingErrorMessage, load }) => (
  <Modal
    modalName="geneBreakdown"
    size="large"
    title={`${loading ? '' : `${geneBreakdown.length} `}Genes from Search Results`}
    trigger={<ButtonLink content="View Gene Breakdown" icon="search" />}
  >
    <DataLoader contentId={searchHash} load={load} loading={false} content>
      <DataTable
        idField="geneId"
        defaultSortColumn="geneSymbol"
        loading={loading}
        emptyContent={loadingErrorMessage}
        data={geneBreakdown}
        columns={COLUMNS}
        fixedWidth
        downloadFileName={`search_results_genes_${searchHash}`}
        downloadTableType="Gene Results"
      />
    </DataLoader>
  </Modal>
))

GeneBreakdown.propTypes = {
  searchHash: PropTypes.string,
  geneBreakdown: PropTypes.arrayOf(PropTypes.object),
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

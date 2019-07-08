import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Popup } from 'semantic-ui-react'

import DataLoader from 'shared/components/DataLoader'
import SearchResultsLink from 'shared/components/buttons/SearchResultsLink'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import Modal from 'shared/components/modal/Modal'
import { GeneDetails } from 'shared/components/panel/variants/VariantGene'
import Family from 'shared/components/panel/family'
import SortableTable from 'shared/components/table/SortableTable'
import { ButtonLink } from 'shared/components/StyledComponents'
import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
} from 'shared/utils/constants'

import {
  getSearchGeneBreakdownValues,
  getSearchGeneBreakdownLoading,
  getSearchGeneBreakdownErrorMessage,
} from '../selectors'
import { loadGeneBreakdown } from '../reducers'

const FAMILY_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSIS_STATUS },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
]

const COLUMNS = [
  {
    name: 'geneSymbol',
    content: 'Gene',
    width: 4,
    noFormatExport: true,
    format: row =>
      <div><ShowGeneModal gene={row} size="large" /><GeneDetails gene={row} margin="0.5em 0.5em 0 0" /></div>,
  },
  {
    name: 'numVariants',
    content: '# Variants',
    width: 2,
    noFormatExport: true,
    format: row =>
      <SearchResultsLink
        geneId={row.geneId}
        projectFamilies={Object.entries(row.families.reduce((acc, { family }) => {
          if (!acc[family.projectGuid]) {
            acc[family.projectGuid] = []
          }
          acc[family.projectGuid].push(family.familyGuid)
          return acc
        }, {})).map(([projectGuid, familyGuids]) => ({ projectGuid, familyGuids }))}
        familyGuids={row.families.map(({ family }) => family.familyGuid)}
        buttonText={row.numVariants.toString()}
        initialSearch={row.search}
      />,
  },
  { name: 'numFamilies', content: '# Families', width: 2, noFormatExport: true },
  {
    name: 'families',
    content: 'Families',
    width: 8,
    format: (row, isExport) => (
      isExport ? row.families.map(({ family, count }) => `${family.displayName} (${count})`).join(', ') :
        row.families.map(({ family, count }, index) =>
          <span key={family.familyGuid}>
            {index > 0 && <span>,&nbsp;</span>}
            <Popup
              hoverable
              flowing
              trigger={<ButtonLink content={family.displayName} />}
              content={<Family family={family} fields={FAMILY_FIELDS} useFullWidth disablePedigreeZoom />}
            />
            ({count})
          </span>)
    ),
  },
]

const GeneBreakdown = ({ searchHash, geneBreakdown, loading, loadingErrorMessage, load }) =>
  <Modal
    modalName="geneBreakdown"
    size="large"
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
        downloadFileName={`search_results_genes_${searchHash}`}
        downloadTableType="Gene Results"
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

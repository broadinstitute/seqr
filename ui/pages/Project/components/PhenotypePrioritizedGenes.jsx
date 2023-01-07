import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import DataLoader from 'shared/components/DataLoader'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import { BaseVariantGene } from 'shared/components/panel/variants/VariantGene'
import { getIndividualPhenotypeGeneScores } from 'shared/components/panel/variants/selectors'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { loadPhenotypeGeneScores } from '../reducers'
import { getPhenotypeDataLoading } from '../selectors'

const PHENOTYPE_GENE_INFO_COLUMNS = [
  {
    name: 'geneId',
    width: 6,
    content: 'Gene',
    format: ({ gene, rowId }) => (
      <BaseVariantGene
        geneId={gene.geneId}
        gene={gene}
        geneModalId={rowId}
        compact
        showInlineDetails
        noExpand
      />
    ),
  },
  { name: 'tool', width: 1, content: 'Tool' },
  {
    name: 'diseaseName',
    width: 3,
    content: 'Disease',
    format: ({ diseaseName, diseaseId }) => (
      <div>
        {diseaseName}
        <br />
        <i>{diseaseId}</i>
      </div>
    ),
  },
  { name: 'rank', width: 1, content: 'Rank' },
  {
    name: 'scores',
    width: 5,
    content: 'Scores',
    format: ({ scores }) => Object.keys(scores).sort().map(scoreName => (
      <div key={scoreName}>
        <b>{camelcaseToTitlecase(scoreName)}</b>
        : &nbsp;
        { scores[scoreName].toPrecision(3) }
      </div>
    )),
  },
]

const BasePhenotypePriGenes = React.memo((
  { individualGuid, phenotypeGeneScores, familyGuid, loading, load },
) => (
  <DataLoader content={phenotypeGeneScores[individualGuid]} contentId={individualGuid} load={load} loading={loading}>
    <GeneSearchLink
      buttonText="Search for variants in high-ranked genes"
      icon="search"
      location={(phenotypeGeneScores[individualGuid] || []).map(({ geneId }) => geneId).join(',')}
      familyGuid={familyGuid}
      floated="right"
    />
    <DataTable
      data={phenotypeGeneScores[individualGuid]}
      idField="rowId"
      columns={PHENOTYPE_GENE_INFO_COLUMNS}
      fixedWidth
      defaultSortColumn="rank"
    />
  </DataLoader>
))

BasePhenotypePriGenes.propTypes = {
  individualGuid: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
  phenotypeGeneScores: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  phenotypeGeneScores: getIndividualPhenotypeGeneScores(state),
  loading: getPhenotypeDataLoading(state),
})

const mapDispatchToProps = {
  load: loadPhenotypeGeneScores,
}

export default connect(mapStateToProps, mapDispatchToProps)(BasePhenotypePriGenes)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getGenesById, getPhenotypeGeneScoresByIndividual } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import { BaseVariantGene } from 'shared/components/panel/variants/VariantGene'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { loadPhenotypeGeneScores } from '../reducers'
import { getPhenotypeDataLoading } from '../selectors'

const PHENOTYPE_GENE_INFO_COLUMNS = [
  {
    name: 'geneId',
    width: 7,
    content: 'Gene',
    format: ({ geneId, gene, variant, familyGuid }) => (
      <div>
        <BaseVariantGene
          geneId={geneId}
          gene={gene}
          variant={variant}
          compact
          showInlineDetails
        />
        <GeneSearchLink
          buttonText="Gene Search"
          icon="search"
          location={geneId}
          familyGuid={familyGuid}
        />
      </div>
    ),
  },
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
  { individual, phenotypeGeneScores, familyGuid, genes, loading, load },
) => (
  <DataLoader content={phenotypeGeneScores} contentId={individual.individualGuid} load={load} loading={loading}>
    <GeneSearchLink
      buttonText="Search for variants in high-ranked genes"
      icon="search"
      location={Object.values(phenotypeGeneScores || {}).map(({ geneId }) => geneId).join(',')}
      familyGuid={familyGuid}
      floated="right"
    />
    <DataTable
      data={Object.entries(phenotypeGeneScores || {}).reduce((acc, [geneId, toolData]) => ([
        ...acc,
        ...Object.values(toolData).reduce((acc2, data) => ([
          ...acc2,
          ...data.map(d => ({
            ...d,
            geneId,
            gene: genes[geneId],
            variant: { variantId: `modalId-${geneId}` },
            familyGuid,
            rowId: `${geneId}${d.diseaseId}`,
          })),
        ]), []),
      ]), [])}
      idField="rowId"
      columns={PHENOTYPE_GENE_INFO_COLUMNS}
      fixedWidth
      defaultSortColumn="rank"
    />
  </DataLoader>
))

BasePhenotypePriGenes.propTypes = {
  individual: PropTypes.object.isRequired,
  familyGuid: PropTypes.string.isRequired,
  phenotypeGeneScores: PropTypes.object,
  genes: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  phenotypeGeneScores: getPhenotypeGeneScoresByIndividual(state)[ownProps.individual.individualGuid],
  genesById: getGenesById(state),
  genes: getGenesById(state),
  loading: getPhenotypeDataLoading(state),
})

const mapDispatchToProps = {
  load: loadPhenotypeGeneScores,
}

export default connect(mapStateToProps, mapDispatchToProps)(BasePhenotypePriGenes)

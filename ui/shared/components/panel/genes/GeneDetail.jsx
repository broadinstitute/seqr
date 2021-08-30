/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Grid, Popup } from 'semantic-ui-react'

import { loadGene, updateGeneNote } from 'redux/rootReducer'
import { getGenesIsLoading, getGenesById, getUser } from 'redux/selectors'
import Gtex from '../../graph/Gtex'
import { SectionHeader } from '../../StyledComponents'
import DataLoader from '../../DataLoader'
import NoteListFieldView from '../view-fields/NoteListFieldView'
import { HorizontalSpacer } from '../../Spacers'


const EXAC_README_URL = 'ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3/functional_gene_constraint/README_forweb_cleaned_exac_r03_2015_03_16_z_data.txt'

const CompactGrid = styled(Grid)`
  padding: 10px !important;
  
  .row {
    padding: 5px !important;
  }
`

const GeneSection = React.memo(({ details }) =>
  <CompactGrid>
    {details.map(row => row &&
      <Grid.Row key={row.title}>
        <Grid.Column width={2} textAlign="right">
          <b>{row.title}</b>
        </Grid.Column>
        <Grid.Column width={14}>{row.content}</Grid.Column>
      </Grid.Row>,
    )}
  </CompactGrid>,
)

GeneSection.propTypes = {
  details: PropTypes.array,
}

const textWithLinks = (text) => {
  const linkMap = {
    PubMed: 'http://www.ncbi.nlm.nih.gov/pubmed/',
    ECO: 'http://ols.wordvis.com/q=ECO:',
    MIM: 'http://www.omim.org/entry/',
  }
  const linkRegex = new RegExp(
    Object.keys(linkMap).map(title => `(${title}:\\d+)`)
      .concat(['(DISEASE:.*?=\\[MIM)', '(;)'])
      .join('|'), 'g')
  return (
    <span>
      {text && text.split(linkRegex).map((str, i) => {
        for (const title of Object.keys(linkMap)) { // eslint-disable-line no-restricted-syntax
          if (str && str.startsWith(`${title}:`)) {
            const id = str.replace(`${title}:`, '')
            return <span key={i}>{title}: <a href={`${linkMap[title]}${id}`} target="_blank">{id}</a></span>
          }
        }
        if (str && str.startsWith('DISEASE:') && str.endsWith('[')) {
          return <span key={i}><b>{str.replace('DISEASE:', '').replace('[', '')}</b> [</span>
        }
        if (str === ';') {
          return <br key={i} />
        }
        return str
      },
      )}
    </span>
  )
}

export const getOtherGeneNames = gene =>
  (gene.geneNames || '').split(';').filter(name => name !== gene.geneSymbol)

const ScoreDetails = ({ scores, fields, note, rankDescription }) => {
  const fieldsToShow = fields.map(({ field, shouldShow, ...config }) => {
    let value = (scores || {})[field]
    if (shouldShow && !shouldShow(value)) {
      value = null
    }
    return { value, ...config }
  }).filter(({ value }) => value)
  return fieldsToShow.length ?
    <div>
      {fieldsToShow.map(({ value, label, rankField }) => value &&
        <span key={label}>
          {label}: {value.toPrecision(4)}
          {rankField && <span> (ranked {scores[rankField]} most {rankDescription} out of {scores.totalGenes} genes under study)</span>}
          <br />
        </span>,
      )}
      <i style={{ color: 'gray' }}>NOTE: {note}</i>
    </div> : 'No score available'
}

ScoreDetails.propTypes = {
  scores: PropTypes.object,
  fields: PropTypes.array,
  note: PropTypes.node,
  rankDescription: PropTypes.string,
}

const STAT_DETAILS = [
  { title: 'Coding Size', content: gene => `${((gene.codingRegionSizeGrch38 || gene.codingRegionSizeGrch37) / 1000).toPrecision(2)}kb` },
  {
    title: 'Missense Constraint',
    scoreField: 'constraints',
    fields: [{ field: 'misZ', rankField: 'misZRank', label: 'z-score' }],
    rankDescription: 'constrained',
    note: (
      <span>
        Missense contraint is a measure of the degree to which the number of missense variants found
        in this gene in ExAC v0.3 is higher or lower than expected according to the statistical model
        described in [
        <a href="http://www.nature.com/ng/journal/v46/n9/abs/ng.3050.html" target="_blank">
          K. Samocha 2014
        </a>]. In general this metric is most useful for genes that act via a dominant mechanism, and where
        a large proportion of the protein is heavily functionally constrained. For more details see
        this <a href={EXAC_README_URL} target="_blank">README</a>.
      </span>
    ),
  },
  {
    title: 'LoF Constraint',
    scoreField: 'constraints',
    fields: [
      { field: 'louef', rankField: 'louefRank', label: 'louef', shouldShow: val => val !== undefined && val !== 100 },
      { field: 'pli', rankField: 'pliRank', label: 'pLI-score' },
    ],
    rankDescription: 'intolerant of LoF mutations',
    note: 'These metrics are based on the amount of expected variation observed in the gnomAD data and is a measure ' +
    'of how likely the gene is to be intolerant of loss-of-function mutations.',
  },
  {
    title: 'Haploinsufficient',
    scoreField: 'cnSensitivity',
    fields: [{ field: 'phi', label: 'pHI-score' }],
    rankDescription: 'intolerant of LoF mutations',
    note: 'These are a score under development by the Talkowski lab that predict whether a gene is haploinsufficient ' +
    'based on large chromosomal microarray data set analysis. Scores >0.84 are considered to have high likelihood to ' +
    'be haploinsufficient.',
  },
  {
    title: 'Triplosensitive',
    scoreField: 'cnSensitivity',
    fields: [{ field: 'pts', label: 'pTS-score' }],
    rankDescription: 'intolerant of LoF mutations',
    note: 'These are a score under development by the Talkowski lab that predict whether a gene is triplosensitive ' +
    'based on large chromosomal microarray dataset analysis. Scores >0.993 are considered to have high likelihood to ' +
    'be triplosensitive.',
  },
]

const GeneDetailContent = React.memo(({ gene, user, updateGeneNote: dispatchUpdateGeneNote }) => {
  if (!gene) {
    return null
  }
  const grch37Coords = gene.startGrch37 && `chr${gene.chromGrch37}:${gene.startGrch37}-${gene.endGrch37}`
  const grch38Coords = gene.startGrch38 && `chr${gene.chromGrch38}:${gene.startGrch38}-${gene.endGrch38}`
  const basicDetails = [
    { title: 'Symbol', content: gene.geneSymbol },
    { title: 'Ensembl ID', content: gene.geneId },
    { title: 'Description', content: textWithLinks(gene.functionDesc) },
    { title: 'Coordinates', content: grch38Coords ? `${grch38Coords} (hg19: ${grch37Coords || 'liftover failed'})` : grch37Coords },
    { title: 'Gene Type', content: gene.gencodeGeneType },
  ]
  const otherGeneNames = getOtherGeneNames(gene)
  if (otherGeneNames.length > 0) {
    basicDetails.splice(1, 0, { title: 'Other Gene Names', content: otherGeneNames.join(', ') })
  }
  const statDetails = STAT_DETAILS.map(({ title, content, scoreField, ...props }) => ({
    title, content: content ? content(gene) : <ScoreDetails scores={gene[scoreField]} {...props} />,
  }))

  const associationDetails = [
    {
      title: 'OMIM',
      content: (gene.omimPhenotypes || []).length > 0 ?
        <div>
          {gene.omimPhenotypes.map(phenotype =>
            <span key={phenotype.phenotypeDescription}>{phenotype.phenotypeMimNumber ?
              <a href={`http://www.omim.org/entry/${phenotype.phenotypeMimNumber}`} target="_blank">
                {phenotype.phenotypeDescription}
              </a>
              : phenotype.phenotypeDescription}
              <br />
            </span>,
          )}
        </div>
        : <em>No disease associations</em>,
    },
  ]
  if (gene.diseaseDesc) {
    associationDetails.push({
      title: 'dbNSFP Details',
      content: textWithLinks(gene.diseaseDesc),
    })
  }
  const linkDetails = [
    gene.mimNumber ? { title: 'OMIM', link: `http://www.omim.org/entry/${gene.mimNumber}`, description: 'Database of Mendelian phenotypes' } : null,
    { title: 'PubMed', link: `http://www.ncbi.nlm.nih.gov/pubmed/?term=(${[gene.geneSymbol, ...otherGeneNames].join(' OR ')})`, description: 'Search PubMed' },
    { title: 'GeneCards', link: `http://www.genecards.org/cgi-bin/carddisp.pl?gene=${gene.geneId}`, description: 'Reference of public data for this gene' },
    { title: 'Protein Atlas', link: `http://www.proteinatlas.org/${gene.geneId}/tissue`, description: 'Detailed protein and transcript expression' },
    { title: 'NCBI Gene', link: `http://www.ncbi.nlm.nih.gov/gene/?term=${gene.geneId}`, description: 'NCBI\'s gene information resource' },
    { title: 'GTEx Portal', link: `http://www.gtexportal.org/home/gene/${gene.geneId}`, description: 'Reference of public data for this gene' },
    { title: 'Monarch', link: `http://monarchinitiative.org/gene/ENSEMBL:${gene.geneId}`, description: 'Cross-species gene and phenotype resource' },
    { title: 'Decipher', link: `https://decipher.sanger.ac.uk/gene/${gene.geneId}/overview/protein-genomic-info`, description: 'DatabasE of genomiC varIation and Phenotype in Humans using Ensembl Resources' },
    { title: 'UniProt', link: `http://www.uniprot.org/uniprot/?random=true&query=${gene.geneId}+AND+reviewed:yes+AND+organism:9606`, description: 'Protein sequence and functional information' },
    { title: 'gnomAD', link: `https://gnomad.broadinstitute.org/gene/${gene.geneId}?dataset=gnomad_r3`, description: 'Genome Aggregation Database' },
    gene.mgiMarkerId ? { title: 'MGI', link: `http://www.informatics.jax.org/marker/${gene.mgiMarkerId}`, description: 'Mouse Genome Informatics' } : null,
    gene.mgiMarkerId ? { title: 'IMPC', link: `https://www.mousephenotype.org/data/genes/${gene.mgiMarkerId}`, description: 'International Mouse Phenotyping Consortium' } : null,
    { title: 'ClinVar', link: `https://www.ncbi.nlm.nih.gov/clinvar?term=${gene.geneSymbol}[gene]`, description: 'Aggregated information about human genomic variation' },
    user.isAnalyst ? { title: 'HGMD', link: `https://my.qiagendigitalinsights.com/bbp/view/hgmd/pro/gene.php?gene=${gene.geneSymbol}`, description: 'Human Gene Mutation Database ' } : null,
  ]
  return (
    <div>
      {linkDetails.filter(linkConfig => linkConfig).map(linkConfig =>
        <Popup
          key={linkConfig.title}
          trigger={<a href={linkConfig.link} target="_blank"><b>{linkConfig.title}</b><HorizontalSpacer width={20} /></a>}
          content={linkConfig.description}
        />,
      )}
      <SectionHeader>Basics</SectionHeader>
      <GeneSection details={basicDetails} />
      <SectionHeader>Stats</SectionHeader>
      <GeneSection details={statDetails} />
      <SectionHeader>Disease Associations</SectionHeader>
      <GeneSection details={associationDetails} />
      <SectionHeader>Shared Notes</SectionHeader>
      <p>
        Information saved here will be shared across seqr. Please consider using this space to share gene-specific
        information you learn while researching candidates.
      </p>
      <NoteListFieldView
        isEditable
        idField="geneId"
        modalTitle="Gene Note"
        initialValues={gene}
        onSubmit={dispatchUpdateGeneNote}
      />
    </div>
  )
})

GeneDetailContent.propTypes = {
  gene: PropTypes.object,
  updateGeneNote: PropTypes.func.isRequired,
  user: PropTypes.object,
}

const GeneDetail = React.memo(({ geneId, gene, user, loading, loadGene: dispatchLoadGene, updateGeneNote: dispatchUpdateGeneNote }) =>
  <div>
    <DataLoader contentId={geneId} content={gene} loading={loading} load={dispatchLoadGene}>
      <GeneDetailContent gene={gene} updateGeneNote={dispatchUpdateGeneNote} user={user} />
    </DataLoader>
    <SectionHeader>Tissue-Specific Expression</SectionHeader>
    <Gtex geneId={geneId} />
  </div>,
)

GeneDetail.propTypes = {
  geneId: PropTypes.string.isRequired,
  gene: PropTypes.object,
  loading: PropTypes.bool.isRequired,
  loadGene: PropTypes.func.isRequired,
  updateGeneNote: PropTypes.func.isRequired,
  user: PropTypes.object,
}

const mapDispatchToProps = {
  loadGene, updateGeneNote,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  loading: getGenesIsLoading(state),
  user: getUser(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(GeneDetail)

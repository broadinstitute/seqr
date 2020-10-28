/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Grid, Popup } from 'semantic-ui-react'

import { loadGene, updateGeneNote } from 'redux/rootReducer'
import { getGenesIsLoading, getGenesById } from 'redux/selectors'
import Gtex from '../../graph/Gtex'
import { SectionHeader } from '../../StyledComponents'
import DataLoader from '../../DataLoader'
import TextFieldView from '../view-fields/TextFieldView'
import { HorizontalSpacer } from '../../Spacers'


const NOTE_STYLE = { display: 'block' }

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

const GeneDetailContent = React.memo(({ gene, updateGeneNote: dispatchUpdateGeneNote }) => {
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
  const constraints = gene.constraints || {}
  const statDetails = [
    { title: 'Coding Size', content: ((gene.codingRegionSizeGrch38 || gene.codingRegionSizeGrch37) / 1000).toPrecision(2) },
    {
      title: 'Missense Constraint',
      content: constraints.misZ ?
        <div>
          z-score: {constraints.misZ.toPrecision(4)} (ranked {constraints.misZRank} most constrained out of
          {constraints.totalGenes} genes under study).
          <br />
          <i style={{ color: 'gray' }}>
            NOTE: Missense contraint is a measure of the degree to which the number of missense variants found
            in this gene in ExAC v0.3 is higher or lower than expected according to the statistical model
            described in [
            <a href="http://www.nature.com/ng/journal/v46/n9/abs/ng.3050.html" target="_blank">
              K. Samocha 2014
            </a>]. In general this metric is most useful for genes that act via a dominant mechanism, and where
            a large proportion of the protein is heavily functionally constrained. For more details see
            this
            <a href="ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3/functional_gene_constraint/README_forweb_cleaned_exac_r03_2015_03_16_z_data.txt" target="_blank">
              {' README'}
            </a>.
          </i>
        </div> : ' No score available',
    },
    {
      title: 'LoF Constraint',
      content: (constraints.pli || (constraints.louef !== undefined && constraints.louef !== 100)) ?
        <div>
          {constraints.louef !== undefined && constraints.louef !== 100 &&
            <span>louef: {constraints.louef.toPrecision(4)} (ranked {constraints.louefRank} most intolerant of LoF
              mutations out of {constraints.totalGenes} genes under study). <br />
            </span>}
          {constraints.pli > 0 &&
            <span>pLI-score: {constraints.pli.toPrecision(4)} (ranked {constraints.pliRank} most intolerant of LoF
              mutations out of {constraints.totalGenes} genes under study). <br />
            </span>}
          <i style={{ color: 'gray' }}>
            NOTE: These metrics are based on the amount of expected variation observed in the gnomAD data and is a
            measure of how likely the gene is to be intolerant of loss-of-function mutations.
          </i>
        </div> : 'No score available',
    },
  ]
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
    { title: 'Decipher', link: `https://decipher.sanger.ac.uk/gene/${gene.geneId}#overview/protein-info`, description: 'DatabasE of genomiC varIation and Phenotype in Humans using Ensembl Resources' },
    { title: 'UniProt', link: `http://www.uniprot.org/uniprot/?random=true&query=${gene.geneId}+AND+reviewed:yes+AND+organism:9606`, description: 'Protein sequence and functional information' },
    gene.mgiMarkerId ? { title: 'MGI', link: `http://www.informatics.jax.org/marker/${gene.mgiMarkerId}`, description: 'Mouse Genome Informatics' } : null,
    gene.mgiMarkerId ? { title: 'IMPC', link: `https://www.mousephenotype.org/data/genes/${gene.mgiMarkerId}`, description: 'International Mouse Phenotyping Consortium' } : null,
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
      {gene.notes && gene.notes.map(geneNote =>
        <TextFieldView
          key={geneNote.noteGuid}
          initialValues={geneNote}
          field="note"
          idField="noteGuid"
          textAnnotation={<i style={{ color: 'gray' }}>By {geneNote.createdBy || 'unknown user'} {geneNote.lastModifiedDate && `(${new Date(geneNote.lastModifiedDate).toLocaleDateString()})`}</i>}
          isEditable={geneNote.editable}
          onSubmit={dispatchUpdateGeneNote}
          modalTitle="Edit Gene Note"
          isDeletable={geneNote.editable}
          deleteConfirm="Are you sure you want to delete this note?"
          style={NOTE_STYLE}
        />,
      )}
      <TextFieldView
        isEditable
        editLabel="Add Note"
        field="note"
        idField="geneId"
        modalTitle="Add Gene Note"
        initialValues={gene}
        onSubmit={dispatchUpdateGeneNote}
        style={NOTE_STYLE}
      />
    </div>
  )
})

GeneDetailContent.propTypes = {
  gene: PropTypes.object,
  updateGeneNote: PropTypes.func.isRequired,
}

const GeneDetail = React.memo(({ geneId, gene, loading, loadGene: dispatchLoadGene, updateGeneNote: dispatchUpdateGeneNote }) =>
  <div>
    <DataLoader contentId={geneId} content={gene} loading={loading} load={dispatchLoadGene}>
      <GeneDetailContent gene={gene} updateGeneNote={dispatchUpdateGeneNote} />
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
}

const mapDispatchToProps = {
  loadGene, updateGeneNote,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  loading: getGenesIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(GeneDetail)

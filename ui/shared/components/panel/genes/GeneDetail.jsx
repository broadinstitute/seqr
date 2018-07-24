/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Grid, Header, Popup } from 'semantic-ui-react'

import { loadGene, updateGeneNote } from 'redux/rootReducer'
import { getGenesIsLoading, getGenesById } from 'redux/selectors'
import SectionHeader from '../../SectionHeader'
import DataLoader from '../../DataLoader'
import TextFieldView from '../view-fields/TextFieldView'
import GeneExpression from './GeneExpression'
import { HorizontalSpacer } from '../../Spacers'


const NOTE_STYLE = { display: 'block' }

const CompactGrid = styled(Grid)`
  padding: 10px !important;
  
  .row {
    padding: 5px !important;
  }
`

const GeneSection = ({ details }) =>
  <CompactGrid>
    {details.map(row => row &&
      <Grid.Row key={row.title}>
        <Grid.Column width={2} textAlign="right">
          <b>{row.title}</b>
        </Grid.Column>
        <Grid.Column width={14}>{row.content}</Grid.Column>
      </Grid.Row>,
    )}
  </CompactGrid>

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
            return <span key={i}>{title}: <a href={`${linkMap[title]}${id}`} target="_blank" rel="noopener noreferrer">{id}</a></span>
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

const GeneDetailContent = ({ gene, showTitle, updateGeneNote: dispatchUpdateGeneNote }) => {
  const basicDetails = [
    { title: 'Symbol', content: gene.symbol },
    { title: 'Ensembl ID', content: gene.gene_id },
    { title: 'Description', content: textWithLinks(gene.function_desc) },
    { title: 'Coordinates', content: `chr${gene.chrom}:${gene.start}-${gene.stop}` },
    { title: 'Gene Type', content: gene.gene_type },
  ]
  const statDetails = [
    { title: 'Coding Size', content: (gene.coding_size / 1000).toPrecision(2) },
    {
      title: 'Missense Constraint',
      content: gene.tags.missense_constraint ?
        <div>
          z-score: {gene.tags.missense_constraint.toPrecision(4)} (ranked {gene.tags.missense_constraint_rank[0]}
          most constrained out of {gene.tags.missense_constraint_rank[1]} genes under study). <br />
          <i style={{ color: 'gray' }}>
            NOTE: Missense contraint is a measure of the degree to which the number of missense variants found
            in this gene in ExAC v0.3 is higher or lower than expected according to the statistical model
            described in [
            <a href="http://www.nature.com/ng/journal/v46/n9/abs/ng.3050.html" target="_blank" rel="noopener noreferrer">
              K. Samocha 2014
            </a>]. In general this metric is most useful for genes that act via a dominant mechanism, and where
            a large proportion of the protein is heavily functionally constrained. For more details see
            this
            <a href="ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3/functional_gene_constraint/README_forweb_cleaned_exac_r03_2015_03_16_z_data.txt" target="_blank" rel="noopener noreferrer">
              {' README'}
            </a>.
          </i>
        </div> : ' No score available',
    },
    {
      title: 'LoF Constraint',
      content: gene.tags.lof_constraint ?
        <div>
          pLI-score: {gene.tags.lof_constraint.toPrecision(4)} (ranked {gene.tags.lof_constraint_rank[0]} most
          intolerant of LoF mutations out of {gene.tags.lof_constraint_rank[1]} genes under study). <br />
          <i style={{ color: 'gray' }}>
            NOTE: This metric is based on the amount of expected variation observed in the ExAC data and is a
            measure of how likely the gene is to be intolerant of loss-of-function mutations.
          </i>
        </div> : 'No score available',
    },
  ]
  const associationDetails = [
    {
      title: 'OMIM',
      content: (gene.phenotype_info && gene.phenotype_info.has_mendelian_phenotype) ?
        <div>
          {gene.phenotype_info.mim_phenotypes.map(phenotype =>
            <span key={phenotype.description}>{phenotype.mim_id ?
              <a href={`http://www.omim.org/entry/${phenotype.mim_id}`} target="_blank" rel="noopener noreferrer">
                {phenotype.description}
              </a>
              : phenotype.description}
              <br />
            </span>,
          )}
          {textWithLinks(gene.disease_desc)}
        </div>
        : <em>No disease associations</em>,
    },
    gene.phenotype_info.orphanet_phenotypes.length > 0 ? {
      title: 'ORPHANET',
      content: gene.phenotype_info.orphanet_phenotypes.map(phenotype =>
        <div key={phenotype.orphanet_id}>
          <a href={`http://www.orpha.net/consor/cgi-bin/Disease_Search.php?lng=EN&data_id=20460&Disease_Disease_Search_diseaseGroup=${phenotype.orphanet_id}`} target="_blank" rel="noopener noreferrer">
            {phenotype.description}
          </a>
        </div>,
      ),
    } : null,
  ]
  const linkDetails = [
    gene.phenotype_info.mim_id ? { title: 'OMIM', link: `http://www.omim.org/entry/${gene.phenotype_info.mim_id}`, description: 'Database of Mendelian phenotypes' } : null,
    { title: 'PubMed', link: `http://www.ncbi.nlm.nih.gov/pubmed/?term=${gene.symbol}`, description: `Search PubMed for ${gene.symbol}` },
    { title: 'GeneCards', link: `http://www.genecards.org/cgi-bin/carddisp.pl?gene=${gene.symbol}`, description: 'Reference of public data for this gene' },
    { title: 'Protein Atlas', link: `http://www.proteinatlas.org/${gene.gene_id}/tissue`, description: 'Detailed protein and transcript expression' },
    { title: 'NCBI Gene', link: `http://www.ncbi.nlm.nih.gov/gene/?term=${gene.symbol}`, description: 'NCBI\'s gene information resource' },
    { title: 'GTEx Portal', link: `http://www.gtexportal.org/home/gene/${gene.gene_id}`, description: 'Reference of public data for this gene' },
    { title: 'Monarch', link: `http://monarchinitiative.org/search/${gene.gene_id}`, description: 'Cross-species gene and phenotype resource' },
    { title: 'Decipher', link: `https://decipher.sanger.ac.uk/gene/${gene.symbol}#overview/protein-info`, description: 'DatabasE of genomiC varIation and Phenotype in Humans using Ensembl Resources' },
    { title: 'UniProt', link: `http://www.uniprot.org/uniprot/?random=true&query=gene:${gene.symbol}+AND+reviewed:yes+AND+organism:9606`, description: 'Protein sequence and functional information' },
  ]
  return (
    <div>
      {showTitle && <Header size="huge" dividing>{gene.symbol}</Header>}
      {linkDetails.map(linkConfig =>
        <Popup
          key={linkConfig.title}
          trigger={<a href={linkConfig.link} target="_blank" rel="noopener noreferrer"><b>{linkConfig.title}</b><HorizontalSpacer width={20} /></a>}
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
      {gene.notes.map(geneNote =>
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
        idField="gene_id"
        modalTitle="Add Gene Note"
        initialValues={gene}
        onSubmit={dispatchUpdateGeneNote}
        style={NOTE_STYLE}
      />
      <SectionHeader>Tissue-Specific Expression</SectionHeader>
      <p>
        This plot shows tissue-specific expression from GTEx release V6. These are normalized expression values with
        units of reads-per-kilobase-per-million (RPKMs) plotted on a log<sub>10</sub> scale, so that lower
        expression is to the left.
      </p>
      <GeneExpression expression={gene.expression} />
    </div>
  )
}

GeneDetailContent.propTypes = {
  gene: PropTypes.object,
  updateGeneNote: PropTypes.func.isRequired,
  showTitle: PropTypes.bool,
}

const GeneDetail = ({ geneId, gene, loading, loadGene: dispatchLoadGene, updateGeneNote: dispatchUpdateGeneNote, showTitle = true }) =>
  <DataLoader contentId={geneId} content={gene} loading={loading} load={dispatchLoadGene}>
    <GeneDetailContent gene={gene} updateGeneNote={dispatchUpdateGeneNote} showTitle={showTitle} />
  </DataLoader>

GeneDetail.propTypes = {
  geneId: PropTypes.string.isRequired,
  gene: PropTypes.object,
  loading: PropTypes.bool.isRequired,
  loadGene: PropTypes.func.isRequired,
  updateGeneNote: PropTypes.func.isRequired,
  showTitle: PropTypes.bool,
}

const mapDispatchToProps = {
  loadGene, updateGeneNote,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  loading: getGenesIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(GeneDetail)

/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Header, Dimmer, Grid } from 'semantic-ui-react'

import { getGenesIsLoading, loadGene, getGenesById, updateGeneNote } from 'redux/rootReducer'
import SectionHeader from '../../SectionHeader'
import TextFieldView from '../view-fields/TextFieldView'
import EditTextButton from '../../buttons/EditTextButton'

// TODO shared 404 component
const Error404 = () => (<Header size="huge" textAlign="center">Error 404: Gene Not Found</Header>)

const GeneSection = ({ details }) =>
  <Grid style={{ padding: '10px' }}>
    {details.map(row => row &&
      <Grid.Row key={row.title} style={{ padding: '5px' }}>
        <Grid.Column width={2} textAlign="right"><b>{row.title}</b></Grid.Column>
        <Grid.Column width={14}>{row.content}</Grid.Column>
      </Grid.Row>,
    )}
  </Grid>

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
          return <span><b key={i}>{str.replace('DISEASE:', '').replace('[', '')}</b> [</span>
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

class GeneDetail extends React.Component
{
  static propTypes = {
    geneId: PropTypes.string.isRequired,
    gene: PropTypes.object,
    loading: PropTypes.bool.isRequired,
    loadGene: PropTypes.func.isRequired,
    updateGeneNote: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    props.loadGene(props.geneId)
  }

  render() {
    const { loading, gene } = this.props
    if (loading) {
      // Loader needs to be in an extra Dimmer to properly show up if it is in a modal (https://github.com/Semantic-Org/Semantic-UI-React/issues/879)
      return <Dimmer inverted active><Loader content="Loading" /></Dimmer>
    }
    else if (gene) {
      return (
        <div>
          <SectionHeader>Basics</SectionHeader>
          <GeneSection details={[
            { title: 'Symbol', content: gene.symbol },
            { title: 'Ensembl ID', content: gene.gene_id },
            { title: 'Description', content: textWithLinks(gene.function_desc) },
            { title: 'Coordinates', content: `chr${gene.chrom}:${gene.start}-${gene.stop}` },
            { title: 'Gene Type', content: gene.gene_type },
          ]}
          />
          <SectionHeader>Stats</SectionHeader>
          <GeneSection details={[
            { title: 'Coding Size', content: (gene.coding_size / 1000).toPrecision(2) },
            {
              title: 'Missense Constraint',
              content: gene.tags.missense_constraint ?
                <div>
                  z-score: {gene.tags.missense_constraint.toPrecision(4)} (ranked
                  {gene.tags.missense_constraint_rank[0]} most constrained out of
                  {gene.tags.missense_constraint_rank[1]} genes under study). <br />
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
          ]}
          />
          <SectionHeader>Disease Associations</SectionHeader>
          <GeneSection details={[
            {
              title: 'OMIM',
              content: (gene.phenotype_info && gene.phenotype_info.has_mendelian_phenotype) ?
                <div>
                  {gene.phenotype_info.mim_phenotypes.map(phenotype =>
                    <span key={phenotype.description}>{phenotype.mim_id ?
                      <a target="_blank" href={`http://www.omim.org/entry/${phenotype.mim_id}`}>
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
                  <a target="_blank" href={`http://www.orpha.net/consor/cgi-bin/Disease_Search.php?lng=EN&data_id=20460&Disease_Disease_Search_diseaseGroup=${phenotype.orphanet_id}`}>
                    {phenotype.description}
                  </a>
                </div>,
              ),
            } : null,
          ]}
          />
          <SectionHeader>Shared Notes</SectionHeader>
          <p>
            Information saved here will be shared across seqr. Please consider using this space to share gene-specific
            information you learn while researching candidates.
          </p>
          {gene.notes.map(geneNote =>
            <TextFieldView
              key={geneNote.note_id}
              initialText={geneNote.note}
              fieldId="note_text"
              textAnnotation={<i style={{ color: 'gray' }}>By {geneNote.user ? geneNote.user.display_name : 'unknown user'} {geneNote.date_saved && `(${geneNote.date_saved})`}</i>}
              isEditable={geneNote.editable}
              textEditorId={`geneNote${geneNote.note_id}`}
              textEditorSubmit={values => this.props.updateGeneNote({ ...geneNote, ...values })}
              textEditorTitle="Edit Gene Note"
              isDeletable={geneNote.editable}
              deleteConfirm="Are you sure you want to delete this note?"
              deleteSubmit={() => this.props.updateGeneNote({ ...geneNote, delete: true })}
            />,
          )}
          <div>
            <EditTextButton
              label="Add Note"
              fieldId="note_text"
              modalTitle="Add Gene Note"
              onSubmit={values => this.props.updateGeneNote({ gene_id: gene.gene_id, ...values })}
              modalId={`addGeneNote${gene.gene_id}`}
            />
          </div>
        </div>
      )
    }
    return <Error404 />
  }
}

const mapDispatchToProps = {
  loadGene, updateGeneNote,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  loading: getGenesIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(GeneDetail)

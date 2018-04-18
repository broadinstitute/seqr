/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Header, Dimmer, Grid } from 'semantic-ui-react'

import { getGenesIsLoading, loadGene, getGenesById } from 'redux/rootReducer'
import SectionHeader from '../../SectionHeader'

// TODO shared 404 component
const Error404 = () => (<Header size="huge" textAlign="center">Error 404: Gene Not Found</Header>)

const GeneSection = ({ details }) =>
  <Grid style={{ padding: '10px' }}>
    {details.map(row =>
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
      .concat(['(DISEASE:.*?)\\[MIM:', '(;)'])
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
        if (str && str.startsWith('DISEASE:')) {
          return <b key={i}>{str.replace('DISEASE:', '')}</b>
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
  }

  constructor(props) {
    super(props)

    props.loadGene(props.geneId)
  }

  render() {
    if (this.props.loading) {
      // Loader needs to be in an extra Dimmer to properly show up if it is in a modal (https://github.com/Semantic-Org/Semantic-UI-React/issues/879)
      return <Dimmer inverted active><Loader content /></Dimmer>
    }
    else if (this.props.gene) {
      return (
        <div>
          <SectionHeader>Basics</SectionHeader>
          <GeneSection details={[
            { title: 'Symbol', content: this.props.gene.symbol },
            { title: 'Ensembl ID', content: this.props.gene.gene_id },
            { title: 'Description', content: textWithLinks(this.props.gene.function_desc) },
            { title: 'Coordinates', content: `chr${this.props.gene.chrom}:${this.props.gene.start}-${this.props.gene.stop}` },
            { title: 'Gene Type', content: this.props.gene.gene_type },
          ]}
          />
        </div>
      )
    }
    return <Error404 />
  }
}

const mapDispatchToProps = {
  loadGene,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  loading: getGenesIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(GeneDetail)

/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Grid, Popup, Loader, Label } from 'semantic-ui-react'

import { loadGene, updateGeneNote } from 'redux/rootReducer'
import { getGenesIsLoading, getGenesById, getUser } from 'redux/selectors'
import { getDecipherGeneLink } from 'shared/utils/constants'
import { SectionHeader, ColoredLabel } from '../../StyledComponents'
import DataLoader from '../../DataLoader'
import NoteListFieldView from '../view-fields/NoteListFieldView'
import { HorizontalSpacer } from '../../Spacers'

const Gtex = React.lazy(() => import('../../graph/Gtex'))

const EXAC_README_URL = 'ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3/functional_gene_constraint/README_forweb_cleaned_exac_r03_2015_03_16_z_data.txt'

const GRAY_STYLE = { color: 'gray' }

const CompactGrid = styled(Grid)`
  padding: 10px !important;
  
  .row {
    padding: 5px !important;
  }
`

const geneSection = details => (
  <CompactGrid>
    {details.map(row => row && (
      <Grid.Row key={row.title}>
        <Grid.Column width={2} textAlign="right">
          <b>{row.title}</b>
        </Grid.Column>
        <Grid.Column width={14}>{row.content}</Grid.Column>
      </Grid.Row>
    ))}
  </CompactGrid>
)

const textWithLinks = (text) => {
  const linkMap = {
    PubMed: 'http://www.ncbi.nlm.nih.gov/pubmed/',
    ECO: 'http://ols.wordvis.com/q=ECO:',
    MIM: 'http://www.omim.org/entry/',
  }
  const linkRegex = new RegExp(
    Object.keys(linkMap).map(title => `(${title}:\\d+)`).concat(['(DISEASE:.*?=\\[MIM)', '(;)']).join('|'), 'g',
  )
  return (
    <span>
      {text && text.split(linkRegex).map((str, i) => {
        Object.keys(linkMap).forEach((title) => {
          if (str && str.startsWith(`${title}:`)) {
            const id = str.replace(`${title}:`, '')
            return (
              <span key={i}>
                {`${title}: `}
                <a href={`${linkMap[title]}${id}`} target="_blank" rel="noreferrer">{id}</a>
              </span>
            )
          }
          return null
        })
        if (str && str.startsWith('DISEASE:') && str.endsWith('[')) {
          return (
            <span key={i}>
              <b>{str.replace('DISEASE:', '').replace('[', '')}</b>
              &nbsp; [
            </span>
          )
        }
        if (str === ';') {
          return <br key={i} />
        }
        return str
      })}
    </span>
  )
}

export const getOtherGeneNames = gene => (gene.geneNames || '').split(';').filter(name => name !== gene.geneSymbol)

const ScoreDetails = ({ scores, fields, note, rankDescription }) => {
  const fieldsToShow = fields.map(({ field, shouldShow, ...config }) => {
    let value = (scores || {})[field]
    if (shouldShow && !shouldShow(value)) {
      value = null
    }
    return { value, ...config }
  }).filter(({ value }) => value)
  return fieldsToShow.length ? (
    <div>
      {fieldsToShow.map(({ value, label, rankField }) => value && (
        <span key={label}>
          {`${label}: ${value.toPrecision(4)} ${rankField ?
            `(ranked ${scores[rankField]} most ${rankDescription} out of ${scores.totalGenes} genes under study)` : ''}`}
          <br />
        </span>
      ))}
      <i style={GRAY_STYLE}>
        NOTE: &nbsp;
        {note}
      </i>
    </div>
  ) : 'No score available'
}

ScoreDetails.propTypes = {
  scores: PropTypes.object,
  fields: PropTypes.arrayOf(PropTypes.object),
  note: PropTypes.node,
  rankDescription: PropTypes.string,
}

const CLINGEN_LABEL_PROPS = {
  'No Evidence': { color: 'grey' },
  'Little Evidence': { color: 'blue' },
  'Emerging Evidence': { color: 'olive' },
  'Sufficient Evidence': { color: 'green' },
  'Gene Associated with Autosomal Recessive Phenotype': {
    color: 'grey',
    basic: true,
    content: 'Gene Associated with AR Phenotype',
  },
  'Dosage Sensitivity Unlikely': { color: 'black', basic: true },
}

export const ClingenLabel = ({ value }) => <Label horizontal size="mini" content={value} {...CLINGEN_LABEL_PROPS[value]} />

ClingenLabel.propTypes = {
  value: PropTypes.string,
}

const DosageSensitivity = ({ gene, clingenField, scoreFields, sensitivityType, threshold }) => (
  <div>
    {gene.clinGen && gene.clinGen[clingenField] && (
      <div>
        <a target="_blank" rel="noreferrer" href={gene.clinGen.href}><b>ClinGen: </b></a>
        <ClingenLabel value={gene.clinGen[clingenField]} />
      </div>
    )}
    <ScoreDetails
      scores={gene.cnSensitivity}
      fields={scoreFields}
      rankDescription="intolerant of LoF mutations"
      note={(
        <span>
          These are a score developed by the Talkowski lab [
          <a href="https://pubmed.ncbi.nlm.nih.gov/35917817" target="_blank" rel="noreferrer">
            Collins et al. 2022
          </a>
          ] that predict whether a gene is &nbsp;
          {sensitivityType}
          &nbsp; based on large chromosomal microarray data set analysis. Scores &gt;
          {threshold}
          &nbsp; are considered to have high likelihood to be &nbsp;
          {sensitivityType}
        </span>
      )}
    />
  </div>
)

DosageSensitivity.propTypes = {
  clingenField: PropTypes.string,
  scoreFields: PropTypes.arrayOf(PropTypes.object),
  sensitivityType: PropTypes.string,
  threshold: PropTypes.string,
  gene: PropTypes.object,
}

export const HI_THRESHOLD = 0.86
export const TS_THRESHOLD = 0.94
export const SHET_THRESHOLD = 0.1
const HAPLOINSUFFICIENT_FIELDS = [{ field: 'phi', label: 'pHaplo' }]
const TRIPLOSENSITIVE_FIELDS = [{ field: 'pts', label: 'pTriplo' }]
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
        <a href="http://www.nature.com/ng/journal/v46/n9/abs/ng.3050.html" target="_blank" rel="noreferrer">
          K. Samocha 2014
        </a>
        ]. In general this metric is most useful for genes that act via a dominant mechanism, and where
        a large proportion of the protein is heavily functionally constrained. For more details see
        this &nbsp;
        <a href={EXAC_README_URL} target="_blank" rel="noreferrer">README</a>
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
    title: 'Shet',
    scoreField: 'sHet',
    fields: [
      { field: 'postMean', label: 'post_mean' },
    ],
    note: (
      <span>
        This score was developed by the Pritchard lab [
        <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10245655" target="_blank" rel="noreferrer">
          Zeng et al 2023
        </a>
        ] to predict gene constraint based on functional and evolutionary information. Scores &gt;
        {SHET_THRESHOLD}
        &nbsp; are considered to have high likelihood to be under extreme selection.
      </span>
    ),
  },
  {
    title: 'Haploinsufficient',
    content: gene => (
      <DosageSensitivity
        gene={gene}
        clingenField="haploinsufficiency"
        scoreFields={HAPLOINSUFFICIENT_FIELDS}
        sensitivityType="haploinsufficient"
        threshold={HI_THRESHOLD}
      />
    ),
  },
  {
    title: 'Triplosensitive',
    content: gene => (
      <DosageSensitivity
        gene={gene}
        clingenField="triplosensitivity"
        scoreFields={TRIPLOSENSITIVE_FIELDS}
        sensitivityType="triplosensitive"
        threshold={TS_THRESHOLD}
      />
    ),
  },
]

const GENCC_COLORS = {
  Definitive: '#276749',
  Strong: '#38a169',
  Moderate: '#68d391',
  Supportive: '#63b3ed',
  Limited: '#fc8181',
}

export const GenCC = ({ genCc }) => genCc.classifications.sort(
  (a, b) => b.date.localeCompare(a.date),
).map(({ classification, disease, moi, date, submitter }) => (
  <div key={submitter}>
    <ColoredLabel horizontal size="mini" minWidth="60px" color={GENCC_COLORS[classification] || 'grey'} content={classification} />
    <b>{submitter}</b>
    {` (${date.split('-')[0]}): `}
    <a target="_blank" rel="noreferrer" href={`https://search.thegencc.org/genes/${genCc.hgncId}`}>{disease}</a>
    <i>{` (${moi})`}</i>
  </div>
))

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
      content: (gene.omimPhenotypes || []).length > 0 ? (
        <div>
          {gene.omimPhenotypes.map(phenotype => (
            <span key={phenotype.phenotypeDescription}>
              {phenotype.phenotypeMimNumber ? (
                <a href={`http://www.omim.org/entry/${phenotype.phenotypeMimNumber}`} target="_blank" rel="noreferrer">
                  {phenotype.phenotypeDescription}
                </a>
              ) : phenotype.phenotypeDescription}
              <br />
            </span>
          ))}
        </div>
      ) : <i>No disease associations</i>,
    },
    {
      title: 'dbNSFP Details',
      content: gene.diseaseDesc ? textWithLinks(gene.diseaseDesc) : <i>None</i>,
    },
    {
      title: 'GenCC',
      content: gene.genCc?.classifications ? <GenCC genCc={gene.genCc} /> : <i>Not Submitted</i>,
    },
  ]
  const linkDetails = [
    gene.mimNumber ? { title: 'OMIM', link: `http://www.omim.org/entry/${gene.mimNumber}`, description: 'Database of Mendelian phenotypes' } : null,
    { title: 'PubMed', link: `http://www.ncbi.nlm.nih.gov/pubmed/?term=(${[gene.geneSymbol, ...otherGeneNames].join(' OR ')})`, description: 'Search PubMed' },
    { title: 'GeneCards', link: `http://www.genecards.org/cgi-bin/carddisp.pl?gene=${gene.geneId}`, description: 'Reference of public data for this gene' },
    { title: 'Protein Atlas', link: `http://www.proteinatlas.org/${gene.geneId}/tissue`, description: 'Detailed protein and transcript expression' },
    { title: 'NCBI Gene', link: `http://www.ncbi.nlm.nih.gov/gene/?term=${gene.geneId}`, description: 'NCBI\'s gene information resource' },
    { title: 'GTEx Portal', link: `http://www.gtexportal.org/home/gene/${gene.geneId}`, description: 'Reference of public data for this gene' },
    { title: 'Monarch', link: `https://monarchinitiative.org/explore?search=${gene.geneSymbol}#search`, description: 'Cross-species gene and phenotype resource' },
    { title: 'Decipher', link: getDecipherGeneLink(gene), description: 'DatabasE of genomiC varIation and Phenotype in Humans using Ensembl Resources' },
    { title: 'UniProt', link: `http://www.uniprot.org/uniprot?query=${gene.geneId}+AND(reviewed:true)+AND(organism_id:9606)`, description: 'Protein sequence and functional information' },
    { title: 'Geno2MP', link: `https://geno2mp.gs.washington.edu/Geno2MP/#/gene/${gene.geneSymbol}/gene/0/0/0`, description: 'Genotype to Mendelian Phenotype' },
    { title: 'gnomAD', link: `https://gnomad.broadinstitute.org/gene/${gene.geneId}?dataset=gnomad_r4`, description: 'Genome Aggregation Database' },
    { title: 'primAD', link: `http://primad.basespace.illumina.com/gene/${gene.geneSymbol}`, description: 'Primate Genome Aggregation Database' },
    gene.mgiMarkerId ? { title: 'MGI', link: `http://www.informatics.jax.org/marker/${gene.mgiMarkerId}`, description: 'Mouse Genome Informatics' } : null,
    gene.mgiMarkerId ? { title: 'IMPC', link: `https://www.mousephenotype.org/data/genes/${gene.mgiMarkerId}`, description: 'International Mouse Phenotyping Consortium' } : null,
    { title: 'KEGG', link: `https://www.kegg.jp/kegg-bin/search_pathway_text?keyword=${gene.geneSymbol}&viewImage=true`, description: 'Pathway maps representing known molecular interaction' },
    gene.clinGen ? { title: 'ClinGen', link: gene.clinGen.href, description: 'ClinGen Dosage Sensitivity' } : null,
    { title: 'ClinVar', link: `https://www.ncbi.nlm.nih.gov/clinvar?term=${gene.geneSymbol}[gene]`, description: 'Aggregated information about human genomic variation' },
    user.isAnalyst ? { title: 'HGMD', link: `https://my.qiagendigitalinsights.com/bbp/view/hgmd/pro/gene.php?gene=${gene.geneSymbol}`, description: 'Human Gene Mutation Database ' } : null,
  ]
  return (
    <div>
      {linkDetails.filter(linkConfig => linkConfig).map(linkConfig => (
        <Popup
          key={linkConfig.title}
          trigger={
            <a href={linkConfig.link} target="_blank" rel="noreferrer">
              <b>{linkConfig.title}</b>
              <HorizontalSpacer width={20} />
            </a>
          }
          content={linkConfig.description}
        />
      ))}
      <SectionHeader>Basics</SectionHeader>
      {geneSection(basicDetails)}
      <SectionHeader>Stats</SectionHeader>
      {geneSection(statDetails)}
      <SectionHeader>Disease Associations</SectionHeader>
      {geneSection(associationDetails)}
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

const GeneDetail = React.memo((
  { geneId, gene, user, loading, loadGene: dispatchLoadGene, updateGeneNote: dispatchUpdateGeneNote },
) => (
  <div>
    <DataLoader contentId={geneId} content={gene} loading={loading} load={dispatchLoadGene}>
      <GeneDetailContent gene={gene} updateGeneNote={dispatchUpdateGeneNote} user={user} />
    </DataLoader>
    <SectionHeader>Tissue-Specific Expression</SectionHeader>
    <React.Suspense fallback={<Loader />}>
      <Gtex geneId={geneId} />
    </React.Suspense>
  </div>
))

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

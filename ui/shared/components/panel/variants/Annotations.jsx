import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import styled from 'styled-components'
import { Popup, Label, Icon, Table } from 'semantic-ui-react'

import {
  getGenesById,
  getTranscriptsById,
  getLocusListIntervalsByChromProject,
  getOmimIntervalsByChrom,
  getFamiliesByGuid,
  getUser,
  getSpliceOutliersByChromFamily,
  getElasticsearchEnabled,
} from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import CopyToClipboardButton from '../../buttons/CopyToClipboardButton'
import SearchResultsLink from '../../buttons/SearchResultsLink'
import Modal from '../../modal/Modal'
import { ButtonLink, HelpIcon } from '../../StyledComponents'
import RnaSeqJunctionOutliersTable from '../../table/RnaSeqJunctionOutliersTable'
import { getOtherGeneNames } from '../genes/GeneDetail'
import Transcripts, { ConsequenceDetails, isManeSelect } from './Transcripts'
import VariantGenes, { GeneLabelContent, omimPhenotypesDetail } from './VariantGene'
import {
  getLocus,
  has37Coords,
  Sequence,
  ProteinSequence,
  TranscriptLink,
  getOverlappedIntervals,
  SPLICE_OUTLIER_OVERLAP_ARGS,
} from './VariantUtils'
import {
  GENOME_VERSION_37, GENOME_VERSION_38, getVariantMainTranscript, SVTYPE_LOOKUP, SVTYPE_DETAILS, SCREEN_LABELS,
  EXTENDED_INTRONIC_DESCRIPTION,
} from '../../../utils/constants'
import { camelcaseToTitlecase } from '../../../utils/stringUtils'

const OverlappedIntervalLabels = React.memo(({ groupedIntervals, variant, getOverlapArgs, getLabels }) => {
  const chromIntervals = groupedIntervals[variant.chrom]
  if (!chromIntervals || chromIntervals.length < 1) {
    return null
  }

  const intervals = getOverlappedIntervals(variant, chromIntervals, ...getOverlapArgs)

  return intervals.length > 0 ? getLabels(intervals).map(({ key, content, ...labelProps }) => (
    <Popup
      key={key}
      trigger={<GeneLabelContent {...labelProps} />}
      content={content}
      size="tiny"
      wide
      hoverable
    />
  )) : null
})

OverlappedIntervalLabels.propTypes = {
  groupedIntervals: PropTypes.object,
  variant: PropTypes.object,
  getOverlapArgs: PropTypes.arrayOf(PropTypes.any),
  getLabels: PropTypes.func,
}

const getSpliceOutlierLabels = overlappedOutliers => ([{
  key: 'splice',
  label: 'RNA splice',
  color: 'pink',
  content: <RnaSeqJunctionOutliersTable basic="very" compact="very" singleLine data={overlappedOutliers} showPopupColumns />,
}])

const mapSpliceOutliersStateToProps = state => ({
  groupedIntervals: getSpliceOutliersByChromFamily(state),
  getOverlapArgs: SPLICE_OUTLIER_OVERLAP_ARGS,
  getLabels: getSpliceOutlierLabels,
})

const SpliceOutlierLabel = connect(mapSpliceOutliersStateToProps)(OverlappedIntervalLabels)

const getOmimLabels = phenotypes => ([{
  key: 'omim',
  label: 'OMIM',
  color: 'orange',
  content: omimPhenotypesDetail(phenotypes, true),
}])

const mapOmimStateToProps = state => ({
  groupedIntervals: getOmimIntervalsByChrom(state),
  getOverlapArgs: [() => 'omim'],
  getLabels: getOmimLabels,
})

const OmimLabel = connect(mapOmimStateToProps)(OverlappedIntervalLabels)

const LargeText = styled.div`
  font-size: 1.2em;
`

const DividedLink = styled.a.attrs({ target: '_blank', rel: 'noreferrer' })`
  padding-left: 4px;
  ::before {
    content: "|";
    padding-right: 4px;
    color: grey;
    cursor: initial;
  }
`

const DividedButtonLink = DividedLink.withComponent(ButtonLink)

const UcscBrowserLink = ({ genomeVersion, chrom, pos, refLength, endOffset, copyPosition }) => {
  const posInt = parseInt(pos, 10)
  const ucscGenomeVersion = genomeVersion === GENOME_VERSION_37 ? '19' : genomeVersion

  const highlight = refLength && `hg${ucscGenomeVersion}.chr${chrom}:${posInt}-${posInt + (refLength - 1)}`
  const highlightQ = highlight ? `highlight=${highlight}&` : ''

  const position = getLocus(chrom, posInt, 10, endOffset || 0)

  const positionSummary = `${chrom}:${posInt}${endOffset ? `-${posInt + endOffset}` : ''}`
  const positionLink = (
    <a href={`http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg${ucscGenomeVersion}&${highlightQ}position=${position}`} target="_blank" rel="noreferrer">
      {positionSummary}
    </a>
  )
  return copyPosition ?
    <CopyToClipboardButton text={positionSummary}>{positionLink}</CopyToClipboardButton> : positionLink
}

UcscBrowserLink.propTypes = {
  genomeVersion: PropTypes.string,
  chrom: PropTypes.string,
  pos: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  refLength: PropTypes.number,
  endOffset: PropTypes.number,
  copyPosition: PropTypes.bool,
}

const VariantPosition = ({ variant, svType, useLiftover }) => {
  let { chrom, pos, end, endChrom, genomeVersion } = variant
  const { ref, rg37LocusEnd } = variant

  const showEndLocation = svType && endChrom
  let endOffset = svType && !showEndLocation && end && end - pos

  if (useLiftover) {
    genomeVersion = variant.liftedOverGenomeVersion
    chrom = variant.liftedOverChrom
    pos = variant.liftedOverPos
    if (rg37LocusEnd) {
      endChrom = rg37LocusEnd.contig
      end = rg37LocusEnd.position
      endOffset = endOffset && end - pos
    } else {
      end = null
    }
  }

  return (
    <span>
      <UcscBrowserLink
        genomeVersion={genomeVersion}
        chrom={chrom}
        pos={pos}
        refLength={ref && ref.length}
        endOffset={endOffset}
        copyPosition={!useLiftover}
      />
      {end && showEndLocation && (
        <span>
          ;&nbsp;
          <UcscBrowserLink genomeVersion={genomeVersion} chrom={endChrom || chrom} pos={end} />
        </span>
      )}
    </span>
  )
}

VariantPosition.propTypes = {
  variant: PropTypes.object,
  useLiftover: PropTypes.bool,
  svType: PropTypes.string,
}

const REGULATORY_FEATURE_LINK = { ensemblEntity: 'Regulation', ensemblKey: 'rf' }
const CONSEQUENCE_FEATURES = [
  { name: 'Regulatory', annotationSections: [[{ title: 'Biotype' }]] },
  { name: 'Motif', annotationSections: [] },
].map(f => ({ ...f, field: `sorted${f.name}FeatureConsequences`, idField: `${f.name.toLowerCase()}FeatureId` }))

const LOF_FILTER_MAP = {
  END_TRUNC: { title: 'End Truncation', message: 'This variant falls in the last 5% of the transcript' },
  INCOMPLETE_CDS: { title: 'Incomplete CDS', message: 'The start or stop codons are not known for this transcript' },
  EXON_INTRON_UNDEF: { title: 'Exon-Intron Boundaries', message: 'The exon/intron boundaries of this transcript are undefined in the EnsEMBL API' },
  SMALL_INTRON: { title: 'Small Intron', message: 'The LoF falls in a splice site of a small (biologically unlikely) intron' },
  NON_CAN_SPLICE: { title: 'Non Canonical Splicing', message: 'This variant falls in a non-canonical splice site (not GT..AG)' },
  NON_CAN_SPLICE_SURR: { title: 'Non Canonical Splicing', message: 'This exon has surrounding splice sites that are non-canonical (not GT..AG)' },
  ANC_ALLELE: { title: 'Ancestral Allele', message: 'The alternate allele reverts the sequence back to the ancestral state' },
  NON_DONOR_DISRUPTING: { title: 'Non Donor Disrupting', message: 'The essential splice donor variant does not disrupt the donor site' },
  NON_ACCEPTOR_DISRUPTING: { title: 'Non Acceptor Disrupting', message: 'The essential splice donor variant does not disrupt the acceptor site' },
  RESCUE_DONOR: { title: 'Rescue Donor', message: 'A splice donor-disrupting variant is rescued by an alternative splice site' },
  RESCUE_ACCEPTOR: { title: 'Rescue Acceptor', message: 'A splice acceptor-disrupting variant is rescued by an alternative splice site' },
  GC_TO_GT_DONOR: { title: 'GC-to-GT Donor', message: 'Essential donor splice variant creates a more canonical splice site' },
  '5UTR_SPLICE': { title: "5'UTR", message: 'Essential splice variant LoF occurs in the UTR of the transcript' },
  '3UTR_SPLICE': { title: "3'UTR", message: 'Essential splice variant LoF occurs in the UTR of the transcript' },
}

const getSvRegion = ({ chrom, endChrom, pos, end }, divider) => {
  const endOffset = endChrom ? 0 : end - pos
  return `${chrom}${divider}${pos}-${pos + endOffset}`
}

const getGeneNames = genes => genes.reduce((acc, gene) => [gene.geneSymbol, ...getOtherGeneNames(gene), ...acc], [])

const getLitSearch = (genes, variations) => {
  let search = `(${getGeneNames(genes).join(' OR ')})`
  if (variations.length) {
    search = `${search} AND (${variations.join(' OR ')})`
  }
  return search
}

const shouldShowNonDefaultTranscriptInfoIcon = (variant, transcript, transcriptsById) => {
  const allVariantTranscripts = Object.values(variant.transcripts || {}).flat() || []
  const canonical = allVariantTranscripts.find(t => t.canonical) || null
  const mane = allVariantTranscripts.find(
    t => isManeSelect(t, transcriptsById) || false,
  ) || null

  const result = canonical !== null &&
    mane !== null &&
    transcript.transcriptId !== canonical.transcriptId &&
    transcript.transcriptId !== mane.transcriptId

  return result
}

const VARIANT_LINKS = [
  {
    name: 'gnomAD',
    shouldShow: variant => !!variant.svType,
    getHref: variant => `https://gnomad.broadinstitute.org/region/${getSvRegion(variant, '-')}?dataset=gnomad_sv_r4`,
  },
  {
    name: 'Decipher',
    shouldShow: ({ svType, genomeVersion }) => !!svType && genomeVersion === GENOME_VERSION_38,
    getHref: variant => `https://www.deciphergenomics.org/search/patients/results?q=${getSvRegion(variant, ':')}`,
  },
  {
    name: 'mitomap',
    shouldShow: ({ svType, chrom }) => !svType && chrom === 'M',
    getHref: () => 'https://www.mitomap.org/foswiki/bin/view/Main/SearchAllele',
  },
  {
    name: 'Mitovisualize',
    shouldShow: ({ svType, chrom, genes }) => !svType && chrom === 'M' && genes.some(
      ({ gencodeGeneType }) => gencodeGeneType === 'Mt-tRNA' || gencodeGeneType === 'Mt-rRNA',
    ),
    getHref: ({ pos, ref, alt }) => `https://www.mitovisualize.org/variant/m-${pos}-${ref}-${alt}`,
  },
  {
    name: 'google',
    shouldShow: ({ genes, variations }) => genes.length && variations.length,
    getHref: ({ genes, variations }) => `https://scholar.google.com/scholar?q=${getLitSearch(genes, variations).replaceAll('=', '')}`,
  },
  {
    name: 'pubmed',
    shouldShow: ({ genes }) => genes.length,
    getHref: ({ genes, variations }) => `https://www.ncbi.nlm.nih.gov/pubmed?term=${getLitSearch(genes, variations)}`,
  },
  {
    name: 'AoU',
    shouldShow: ({ svType }) => !svType,
    getHref: ({ chrom, pos, ref, alt }) => `https://databrowser.researchallofus.org/variants/${chrom}-${pos}-${ref}-${alt}`,
  },
  {
    name: 'Iranome',
    shouldShow: ({ svType, chrom }) => !svType && chrom !== 'M',
    getHref: ({ chrom, pos, ref, alt }) => `https://www.iranome.com/variant/${chrom}-${pos}-${ref}-${alt}`,
  },
  {
    name: 'Geno2MP',
    shouldShow: ({ svType, chrom }) => !svType && chrom !== 'M',
    getHref: ({ chrom, pos }) => `https://geno2mp.gs.washington.edu/Geno2MP/#/gene/${chrom}:${pos}/chrLoc/${pos}/${pos}/${chrom}`,
  },
  {
    name: 'Mastermind',
    shouldShow: ({ svType, hgvsc }) => !svType && hgvsc,
    getHref: ({ genes, hgvsc }) => `https://mastermind.genomenon.com/detail?gene=${genes[0].geneSymbol}&mutation=${genes[0].geneSymbol}:${hgvsc}`,
  },
  {
    name: 'BCH',
    shouldShow: (variant, user) => has37Coords(variant) && user.isAnalyst,
    getHref: ({ chrom, pos, ref, alt, genomeVersion, liftedOverPos }) => (
      `https://aggregator.bchresearch.org/variant.html?variant=${chrom}:${genomeVersion === GENOME_VERSION_37 ? pos : liftedOverPos}:${ref}:${alt}`
    ),
  },
  {
    name: 'LitVar2',
    shouldShow: ({ CAID, rsid }) => !!CAID && !!rsid,
    getHref: ({ CAID, rsid }) => (
      `https://ncbi.nlm.nih.gov/research/litvar2/docsum?variant=litvar@${CAID}%23${rsid}%23%23&query=${CAID}`
    ),
  },
]

const getSampleType = (genotypes) => {
  const sampleTypes = [...new Set(Object.values(genotypes || {}).map(({ sampleType }) => sampleType).filter(s => s))]
  return sampleTypes.length === 1 ? sampleTypes[0] : ''
}

const variantSearchLinks = (variant, mainTranscript, genesById, user, elasticsearchEnabled) => {
  const { chrom, endChrom, pos, end, ref, alt, genomeVersion, genotypes, svType, variantId, transcripts } = variant

  const mainGene = genesById[mainTranscript.geneId]
  let genes
  let hgvsc
  const variations = []

  if (mainGene) {
    genes = [mainGene]

    if (ref) {
      variations.unshift(`${pos}${ref}/${alt}`, `${pos}${ref}>${alt}`, `g.${pos}${ref}>${alt}`)
    }

    if (mainTranscript.hgvsp) {
      const hgvsp = mainTranscript.hgvsp.split(':')[1].replace('p.', '')
      variations.unshift(`p.${hgvsp}`, hgvsp)
    }

    if (mainTranscript.hgvsc) {
      hgvsc = mainTranscript.hgvsc.split(':')[1].replace('c.', '')
      variations.unshift(
        `c.${hgvsc}`, // c.1282C>T
        hgvsc, // 1282C>T
        (`c.${hgvsc}`).replace('>', '/'), // c.1282C/T
        hgvsc.replace('>', '/'), // 1282C/T
      )
    }
  } else {
    genes = Object.keys(transcripts || {}).map(geneId => genesById[geneId]).filter(gene => gene)
  }

  const linkVariant = { genes, variations, hgvsc, ...variant }

  const seqrSearchLink = elasticsearchEnabled ? (
    <SearchResultsLink
      buttonText="seqr"
      genomeVersion={genomeVersion}
      svType={svType}
      variantId={svType ? null : variantId}
      location={svType && (
        (endChrom && endChrom !== chrom) ? `${chrom}:${pos - 50}-${pos + 50}` : `${chrom}:${pos}-${end}%20`)}
    />
  ) : (
    <NavLink
      to={`/summary_data/variant_lookup?variantId=${variantId}&genomeVersion=${genomeVersion}&sampleType=${getSampleType(genotypes)}`}
      target="_blank"
    >
      seqr
    </NavLink>
  )

  return [
    <Popup
      key="seqr-search"
      trigger={seqrSearchLink}
      content={`Search for this variant across all your seqr projects${svType ? '. Any structural variant with ≥20% reciprocal overlap will be returned.' : ''}`}
      size="tiny"
    />,
    ...VARIANT_LINKS.filter(({ shouldShow }) => shouldShow(linkVariant, user)).map(
      ({ name, getHref }) => <DividedLink key={name} href={getHref(linkVariant)}>{name}</DividedLink>,
    ),
  ]
}

class BaseSearchLinks extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    mainTranscript: PropTypes.object,
    genesById: PropTypes.object,
    user: PropTypes.object,
    elasticsearchEnabled: PropTypes.bool,
  }

  state = { showAll: false }

  show = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { variant, mainTranscript, genesById, user, elasticsearchEnabled } = this.props
    const { showAll } = this.state

    const links = variantSearchLinks(variant, mainTranscript, genesById, user, elasticsearchEnabled)
    if (links.length < 5) {
      return links
    }
    if (showAll) {
      return [...links.slice(0, 5), <br key="break" />, ...links.slice(5)]
    }

    return [
      ...links.slice(0, 3),
      <DividedButtonLink key="show" icon="ellipsis horizontal" size="mini" padding="0 4px" onClick={this.show} />,
    ]
  }

}

const mapStateToProps = state => ({
  genesById: getGenesById(state),
  user: getUser(state),
  elasticsearchEnabled: getElasticsearchEnabled(state),
})

const SearchLinks = connect(mapStateToProps)(BaseSearchLinks)

const getLocusListLabels = locusLists => locusLists.map(({ locusListGuid, name, description }) => ({
  color: 'teal',
  maxWidth: '8em',
  key: locusListGuid,
  label: name,
  content: description,
}))

const mapLocusListStateToProps = (state, ownProps) => ({
  groupedIntervals: getLocusListIntervalsByChromProject(state, ownProps),
  getOverlapArgs: [fGuid => getFamiliesByGuid(state)[fGuid].projectId],
  getLabels: getLocusListLabels,
})

const VariantLocusListLabels = connect(mapLocusListStateToProps)(OverlappedIntervalLabels)

const svSizeDisplay = (size) => {
  if (size < 1000) {
    return `${size}bp`
  }
  if (size < 1000000) {
    // dividing by 1 removes trailing 0s
    return `${((size) / 1000).toPrecision(3) / 1}kb`
  }
  return `${(size / 1000000).toFixed(2) / 1}Mb`
}

const getLofDetails = ({ isLofNagnag, lofFilters, lofFilter, lofFlags, lof }) => {
  const isNagnag = isLofNagnag || lofFlags === 'NAGNAG_SITE'
  const filters = lofFilters || (lof === 'LC' && lofFilter && lofFilter.split(/&|,/g))
  return (filters || isNagnag) ? [
    ...(filters ? [...new Set(filters)] : []).map((lofFilterKey) => {
      const filter = LOF_FILTER_MAP[lofFilterKey] || { message: lofFilterKey }
      return (
        <div key={lofFilterKey}>
          <b>{`LOFTEE: ${filter.title}`}</b>
          <br />
          {filter.message}
        </div>
      )
    }),
    isNagnag ? (
      <div key="NAGNAG_SITE">
        <b>LOFTEE: NAGNAG site</b>
        <br />
        This acceptor site is rescued by another adjacent in-frame acceptor site.
      </div>
    ) : null,
  ] : null
}

// Adapted from https://github.com/ImperialCardioGenetics/UTRannotator/blob/master/README.md#the-detailed-annotation-for-each-consequence
const UTR_ANNOTATOR_DESCRIPTIONS = {
  AltStop: 'Whether there is an alternative stop codon downstream within 5’ UTR',
  AltStopDistanceToCDS: 'The distance between the alternative stop codon (if exists) and CDS',
  CapDistanceToStart: 'The distance (number of nucleotides) to the start of 5’UTR',
  DistanceToCDS: 'The distance (number of nucleotides) to CDS',
  DistanceToStop: 'The distance (number of nucleotides) to the nearest stop codon (scanning through both the 5’UTR and its downstream CDS)',
  Evidence: 'Whether the disrupted uORF has any translation evidence',
  FrameWithCDS: 'The frame of the uORF with respect to CDS, described by inFrame or outOfFrame',
  KozakContext: 'The Kozak context sequence',
  KozakStrength: 'The Kozak strength, described by one of the following values: Weak, Moderate or Strong',
  StartDistanceToCDS: 'The distance between the disrupting uORF and CDS',
  alt_type: 'The type of uORF with the alternative allele, described by one of following: uORF, inframe_oORF or OutOfFrame_oORF',
  alt_type_length: 'The length of uORF with the alt allele',
  newSTOPDistanceToCDS: 'The distance between the gained uSTOP to the start of the CDS',
  ref_StartDistanceToCDS: 'The distance between the uAUG of the disrupting uORF to CDS',
  ref_type: 'The type of uORF with the reference allele, described by one of following: uORF, inframe_oORF or OutOfFrame_oORF',
  ref_type_length: 'The length of uORF with the reference allele',
  type: 'The type of of 5’ UTR ORF, described by one of the following: uORF(with a stop codon in 5’UTR), inframe_oORF (inframe and overlapping with CDS),OutOfFrame_oORF (out of frame and overlapping with CDS)',
}

const UtrAnnotatorDetail = ({ fiveutrConsequence, fiveutrAnnotation, ...counts }) => (
  <Table compact singleLine basic="very">
    <Table.Body>
      <Table.Row>
        <Table.HeaderCell textAlign="right" content="5' UTR Consequence" />
        <Table.Cell content={fiveutrConsequence} />
      </Table.Row>
      {Object.entries(counts).map(([field, value]) => (
        <Table.Row key={field}>
          <Table.HeaderCell textAlign="right" content={camelcaseToTitlecase(field)} />
          <Table.Cell content={value} />
        </Table.Row>
      ))}
      {Object.entries(fiveutrAnnotation).filter(e => e[1] !== null).map(([field, value]) => (
        <Table.Row key={field}>
          <Table.HeaderCell textAlign="right">
            {camelcaseToTitlecase(field)}
            {UTR_ANNOTATOR_DESCRIPTIONS[field] && (
              <Popup trigger={<HelpIcon color="black" />} content={UTR_ANNOTATOR_DESCRIPTIONS[field]} flowing />
            )}
          </Table.HeaderCell>
          <Table.Cell content={value} />
        </Table.Row>
      ))}
    </Table.Body>
  </Table>
)

UtrAnnotatorDetail.propTypes = {
  fiveutrConsequence: PropTypes.string,
  fiveutrAnnotation: PropTypes.object,
}

const Annotations = React.memo(({ variant, mainGeneId, showMainGene, transcriptsById }) => {
  const {
    rsid, svType, numExon, pos, end, svTypeDetail, svSourceDetail, cpxIntervals, algorithms, bothsidesSupport,
    endChrom, CAID,
  } = variant
  const mainTranscript = getVariantMainTranscript(variant)
  const lofDetails = getLofDetails(mainTranscript.loftee || mainTranscript)

  const transcriptPopupProps = mainTranscript.transcriptId && {
    content: <TranscriptLink variant={variant} transcript={mainTranscript} />,
    size: 'mini',
    hoverable: true,
  }

  const nonMajorConsequences = (mainTranscript.consequenceTerms || []).filter(
    c => c !== mainTranscript.majorConsequence,
  ).map(c => c.replace(/_/g, ' '))

  return (
    <div>
      {(mainTranscript.majorConsequence || svType) && (
        <div>
          <Modal
            modalName={`${variant.variantId}-annotations`}
            title="Transcripts"
            size="large"
            trigger={
              <ButtonLink size={svType && 'big'}>
                {svType ? (SVTYPE_LOOKUP[svType] || svType) : mainTranscript.majorConsequence.replace(/_/g, ' ')}
                {svType && (svTypeDetail || svSourceDetail) && (
                  <Popup
                    trigger={<Icon name="info circle" size="small" corner="top right" />}
                    content={
                      <div>
                        {(SVTYPE_DETAILS[svType] || {})[svTypeDetail] || svTypeDetail || ''}
                        {svTypeDetail && <br />}
                        {svSourceDetail && `Inserted from chr${svSourceDetail.chrom}`}
                      </div>
                    }
                    position="top center"
                  />
                )}
              </ButtonLink>
            }
            popup={transcriptPopupProps}
          >
            <Transcripts variant={variant} />
          </Modal>
          <HorizontalSpacer width={2} />
          {shouldShowNonDefaultTranscriptInfoIcon(variant, mainTranscript, transcriptsById) && (
            <span>
              <Popup
                trigger={<Icon name="info circle" color="yellow" />}
                content={
                  <div>
                    This transcript is neither the Gencode Canonical transcript nor the MANE transcript.
                    It has been selected by seqr as it has the most severe consequence for the variant
                    given your search parameters.
                    Click on the consequence to see alternate transcripts which may have other consequences.
                  </div>
                }
                position="top left"
              />
            </span>
          )}
        </div>
      )}
      {svType && end && !endChrom && end !== pos && (
        <b>
          <HorizontalSpacer width={5} />
          {svSizeDisplay(end - pos)}
        </b>
      )}
      {(algorithms || bothsidesSupport) && (
        <b>
          <HorizontalSpacer width={5} />
          <Popup
            trigger={<Icon name="help circle" />}
            content={
              <div>
                {algorithms && `Algorithms: ${algorithms}.`}
                {bothsidesSupport && (
                  <div>
                    Bothsides Support
                  </div>
                )}
              </div>
            }
            position="top center"
          />
        </b>
      )}
      {Number.isInteger(numExon) && (
        <b>
          {`, ${numExon} exons`}
          <Popup
            trigger={<HelpIcon />}
            content="CNV size and exon number are estimated from exome data and should be confirmed by an alternative method"
          />
        </b>
      )}
      {lofDetails && (
        <span>
          <HorizontalSpacer width={12} />
          <Popup
            trigger={<Label color="red" horizontal size="tiny">LC LoF</Label>}
            content={lofDetails}
          />
        </span>
      )}
      {nonMajorConsequences.length > 0 && (
        <div>
          <b>Additonal VEP consequences: &nbsp;</b>
          {nonMajorConsequences.join('; ')}
        </div>
      )}
      {mainTranscript.spliceregion?.extended_intronic_splice_region_variant && (
        <div>
          <b>Extended Intronic Splice Region</b>
          <Popup trigger={<HelpIcon />} content={EXTENDED_INTRONIC_DESCRIPTION} />
        </div>
      )}
      {mainTranscript.utrannotator?.fiveutrConsequence && (
        <div>
          <b>UTRAnnotator: &nbsp;</b>
          <Modal
            modalName={`${variant.variantId}-utrannotator`}
            title="UTRAnnotator"
            trigger={
              <ButtonLink>
                {mainTranscript.utrannotator.fiveutrConsequence.replace('5_prime_UTR_', '').replace('_variant', '').replace(/_/g, ' ')}
              </ButtonLink>
            }
          >
            <UtrAnnotatorDetail {...mainTranscript.utrannotator} />
          </Modal>
        </div>
      )}
      {variant.screenRegionType && (
        <div>
          <b>
            SCREEN: &nbsp;
            {SCREEN_LABELS[variant.screenRegionType] || variant.screenRegionType}
          </b>
        </div>
      )}
      {CONSEQUENCE_FEATURES.filter(({ field }) => variant[field]).map(({ field, name, ...props }) => (
        <div>
          <b>{`${name} Feature: `}</b>
          <Modal
            modalName={`${variant.variantId}-${name}`}
            title={`${name} Feature Consequences`}
            trigger={<ButtonLink>{variant[field][0].consequenceTerms[0].replace(/_/g, ' ')}</ButtonLink>}
          >
            <ConsequenceDetails
              consequences={variant[field]}
              variant={variant}
              ensemblLink={REGULATORY_FEATURE_LINK}
              {...props}
            />
          </Modal>
        </div>
      ))}
      {mainTranscript.hgvsc && (
        <div>
          <b>HGVS.C</b>
          <HorizontalSpacer width={5} />
          <ProteinSequence hgvs={mainTranscript.hgvsc} />
        </div>
      )}
      {mainTranscript.hgvsp && (
        <div>
          <b>HGVS.P</b>
          <HorizontalSpacer width={5} />
          <ProteinSequence hgvs={mainTranscript.hgvsp} />
        </div>
      )}
      { (svType || Object.keys(mainTranscript).length > 0) && <VerticalSpacer height={10} />}
      {mainGeneId && <VariantGenes mainGeneId={mainGeneId} showMainGene={showMainGene} variant={variant} />}
      {(mainGeneId && Object.keys(variant.transcripts || {}).length > 1) && <VerticalSpacer height={10} />}
      <LargeText>
        <b><VariantPosition variant={variant} svType={svType} /></b>
        <HorizontalSpacer width={10} />
        {variant.ref && (
          <span>
            <Sequence sequence={variant.ref} />
            <Icon name="angle right" />
            <Sequence sequence={variant.alt} />
          </span>
        )}
      </LargeText>
      {rsid && (
        <div>
          <a href={`http://www.ncbi.nlm.nih.gov/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=${rsid}`} target="_blank" rel="noreferrer">
            {rsid}
          </a>
        </div>
      )}
      {CAID && (
        <div>
          <a href={`https://reg.clinicalgenome.org/redmine/projects/registry/genboree_registry/by_canonicalid?canonicalid=${CAID}`} target="_blank" rel="noreferrer">
            {CAID}
          </a>
        </div>
      )}
      {variant.liftedOverGenomeVersion === GENOME_VERSION_37 && (
        variant.liftedOverPos ? (
          <div>
            hg19:
            <VariantPosition variant={variant} svType={svType} useLiftover />
          </div>
        ) : <div>hg19: liftover failed</div>
      )}
      {cpxIntervals && cpxIntervals.length > 0 &&
      [<VerticalSpacer height={5} key="vspace" />, ...cpxIntervals.map(
        e => `${SVTYPE_LOOKUP[e.type] || e.type} ${e.chrom}-${e.start}-${e.end}`,
      ).map(e => <div key={e}>{e}</div>)]}
      <VerticalSpacer height={5} />
      <VariantLocusListLabels variant={variant} familyGuids={variant.familyGuids} />
      <SpliceOutlierLabel variant={variant} />
      <OmimLabel variant={variant} />
      <VerticalSpacer height={5} />
      <SearchLinks variant={variant} mainTranscript={mainTranscript} />
    </div>
  )
})

Annotations.propTypes = {
  variant: PropTypes.object,
  mainGeneId: PropTypes.string,
  showMainGene: PropTypes.bool,
  transcriptsById: PropTypes.object.isRequired,
}

const mapAnnotationsStateToProps = state => ({
  transcriptsById: getTranscriptsById(state),
})

export default connect(mapAnnotationsStateToProps)(Annotations)

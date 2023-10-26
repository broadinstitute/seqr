import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Popup, Label, Icon } from 'semantic-ui-react'

import {
  getGenesById,
  getLocusListIntervalsByChromProject,
  getFamiliesByGuid,
  getUser,
  getSpliceOutliersByChromFamily,
} from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import SearchResultsLink from '../../buttons/SearchResultsLink'
import Modal from '../../modal/Modal'
import { ButtonLink, HelpIcon } from '../../StyledComponents'
import RnaSeqJunctionOutliersTable from '../../table/RnaSeqJunctionOutliersTable'
import { getOtherGeneNames } from '../genes/GeneDetail'
import Transcripts from './Transcripts'
import VariantGenes, { LocusListLabels } from './VariantGene'
import {
  getLocus,
  has37Coords,
  Sequence,
  ProteinSequence,
  TranscriptLink,
  getOverlappedIntervals,
  getOverlappedSpliceOutliers,
} from './VariantUtils'
import {
  GENOME_VERSION_37, GENOME_VERSION_38, getVariantMainTranscript, SVTYPE_LOOKUP, SVTYPE_DETAILS, SCREEN_LABELS,
} from '../../../utils/constants'

const BaseSpliceOutlierLabel = React.memo(({ variant, spliceOutliersByFamily }) => {
  if (!spliceOutliersByFamily || spliceOutliersByFamily.length < 1) {
    return null
  }

  const overlappedOutliers = getOverlappedSpliceOutliers(variant, spliceOutliersByFamily)

  if (overlappedOutliers.length < 1) {
    return null
  }

  return (
    <Popup
      trigger={<Label size="mini" content={<span>RNA splice</span>} color="pink" />}
      content={<RnaSeqJunctionOutliersTable basic="very" compact="very" singleLine data={overlappedOutliers} showPopupColumns />}
      size="tiny"
      wide
      hoverable
    />
  )
})

BaseSpliceOutlierLabel.propTypes = {
  spliceOutliersByFamily: PropTypes.object,
  variant: PropTypes.object,
}

const mapSpliceOutliersStateToProps = (state, ownProps) => ({
  spliceOutliersByFamily: getSpliceOutliersByChromFamily(state)[ownProps.variant.chrom],
})

const SpliceOutlierLabel = connect(mapSpliceOutliersStateToProps)(BaseSpliceOutlierLabel)

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

const UcscBrowserLink = ({ genomeVersion, chrom, pos, refLength, endOffset }) => {
  const posInt = parseInt(pos, 10)
  const ucscGenomeVersion = genomeVersion === GENOME_VERSION_37 ? '19' : genomeVersion

  const highlight = refLength && `hg${ucscGenomeVersion}.chr${chrom}:${posInt}-${posInt + (refLength - 1)}`
  const highlightQ = highlight ? `highlight=${highlight}&` : ''

  const position = getLocus(chrom, posInt, 10, endOffset || 0)

  return (
    <a href={`http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg${ucscGenomeVersion}&${highlightQ}position=${position}`} target="_blank" rel="noreferrer">
      {`${chrom}:${posInt}${endOffset ? `-${posInt + endOffset}` : ''}`}
    </a>
  )
}

UcscBrowserLink.propTypes = {
  genomeVersion: PropTypes.string,
  chrom: PropTypes.string,
  pos: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  refLength: PropTypes.number,
  endOffset: PropTypes.number,
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

const getSvRegion = (
  { chrom, endChrom, pos, end, liftedOverGenomeVersion, liftedOverPos }, divider, useLiftoverVersion,
) => {
  const endOffset = endChrom ? 0 : end - pos
  const start = (useLiftoverVersion && liftedOverGenomeVersion === useLiftoverVersion) ? liftedOverPos : pos
  return `${chrom}${divider}${start}-${start + endOffset}`
}

const getGeneNames = genes => genes.reduce((acc, gene) => [gene.geneSymbol, ...getOtherGeneNames(gene), ...acc], [])

const getLitSearch = (genes, variations) => {
  let search = `(${getGeneNames(genes).join(' OR ')})`
  if (variations.length) {
    search = `${search} AND (${variations.join(' OR ')})`
  }
  return search
}

const VARIANT_LINKS = [
  {
    name: 'gnomAD',
    shouldShow: variant => !!variant.svType && has37Coords(variant),
    getHref: variant => `https://gnomad.broadinstitute.org/region/${getSvRegion(variant, '-', GENOME_VERSION_37)}?dataset=gnomad_sv_r2_1`,
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
    getHref: ({ chrom, pos, ref, alt }) => `https://databrowser.researchallofus.org/genomic-variants/${chrom}-${pos}-${ref}-${alt}`,
  },
  {
    name: 'Iranome',
    shouldShow: ({ svType, chrom }) => !svType && chrom !== 'M',
    getHref: ({ chrom, pos, ref, alt }) => `http://www.iranome.ir/variant/${chrom}-${pos}-${ref}-${alt}`,
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
]

const variantSearchLinks = (variant, mainTranscript, genesById, user) => {
  const { chrom, endChrom, pos, end, ref, alt, genomeVersion, svType, variantId, transcripts } = variant

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

  return [
    <Popup
      key="seqr-search"
      trigger={(
        <SearchResultsLink
          buttonText="seqr"
          genomeVersion={genomeVersion}
          svType={svType}
          variantId={svType ? null : variantId}
          location={svType && (
            (endChrom && endChrom !== chrom) ? `${chrom}:${pos - 50}-${pos + 50}` : `${chrom}:${pos}-${end}%20`)}
        />
      )}
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
  }

  state = { showAll: false }

  show = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { variant, mainTranscript, genesById, user } = this.props
    const { showAll } = this.state

    const links = variantSearchLinks(variant, mainTranscript, genesById, user)
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
})

const SearchLinks = connect(mapStateToProps)(BaseSearchLinks)

const BaseVariantLocusListLabels = React.memo(({ locusListIntervalsByProject, familiesByGuid, variant }) => {
  if (!locusListIntervalsByProject || locusListIntervalsByProject.length < 1) {
    return null
  }

  const locusListGuids = getOverlappedIntervals(variant, locusListIntervalsByProject,
    fGuid => familiesByGuid[fGuid].projectId).map(({ locusListGuid }) => locusListGuid)

  return locusListGuids.length > 0 && <LocusListLabels locusListGuids={locusListGuids} />
})

BaseVariantLocusListLabels.propTypes = {
  locusListIntervalsByProject: PropTypes.object,
  familiesByGuid: PropTypes.object,
  variant: PropTypes.object,
}

const mapLocusListStateToProps = (state, ownProps) => ({
  locusListIntervalsByProject: getLocusListIntervalsByChromProject(state, ownProps)[ownProps.variant.chrom],
  familiesByGuid: getFamiliesByGuid(state),
})

const VariantLocusListLabels = connect(mapLocusListStateToProps)(BaseVariantLocusListLabels)

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

const Annotations = React.memo(({ variant, mainGeneId, showMainGene }) => {
  const {
    rsid, svType, numExon, pos, end, svTypeDetail, svSourceDetail, cpxIntervals, algorithms, bothsidesSupport,
    endChrom,
  } = variant
  const mainTranscript = getVariantMainTranscript(variant)

  const isLofNagnag = mainTranscript.isLofNagnag || mainTranscript.lofFlags === 'NAGNAG_SITE'
  const lofFilters = mainTranscript.lofFilters || (
    mainTranscript.lof === 'LC' && mainTranscript.lofFilter && mainTranscript.lofFilter.split(/&|,/g)
  )
  const lofDetails = (lofFilters || isLofNagnag) ? [
    ...(lofFilters ? [...new Set(lofFilters)] : []).map((lofFilterKey) => {
      const lofFilter = LOF_FILTER_MAP[lofFilterKey] || { message: lofFilterKey }
      return (
        <div key={lofFilterKey}>
          <b>{`LOFTEE: ${lofFilter.title}`}</b>
          <br />
          {lofFilter.message}
        </div>
      )
    }),
    isLofNagnag ? (
      <div key="NAGNAG_SITE">
        <b>LOFTEE: NAGNAG site</b>
        <br />
        This acceptor site is rescued by another adjacent in-frame acceptor site.
      </div>
    ) : null,
  ] : null

  const transcriptPopupProps = mainTranscript.transcriptId && {
    content: <TranscriptLink variant={variant} transcript={mainTranscript} />,
    size: 'mini',
    hoverable: true,
  }

  return (
    <div>
      {(mainTranscript.majorConsequence || svType) && (
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
      {variant.highConstraintRegion && (
        <span>
          <HorizontalSpacer width={12} />
          <Label color="red" horizontal size="tiny">High Constraint Region</Label>
        </span>
      )}
      {variant.screenRegionType && (
        <div>
          <b>
            SCREEN: &nbsp;
            {SCREEN_LABELS[variant.screenRegionType] || variant.screenRegionType}
          </b>
        </div>
      )}
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
      <VerticalSpacer height={5} />
      <SearchLinks variant={variant} mainTranscript={mainTranscript} />
    </div>
  )
})

Annotations.propTypes = {
  variant: PropTypes.object,
  mainGeneId: PropTypes.string,
  showMainGene: PropTypes.bool,
}

export default Annotations

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Popup, Label, Icon } from 'semantic-ui-react'

import { getGenesById, getLocusListIntervalsByChromProject, getFamiliesByGuid } from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import SearchResultsLink from '../../buttons/SearchResultsLink'
import Modal from '../../modal/Modal'
import { ButtonLink, HelpIcon } from '../../StyledComponents'
import { getOtherGeneNames } from '../genes/GeneDetail'
import Transcripts from './Transcripts'
import VariantGenes, { LocusListLabels } from './VariantGene'
import { getLocus, Sequence, ProteinSequence, TranscriptLink } from './VariantUtils'
import { GENOME_VERSION_37, getVariantMainTranscript, SVTYPE_LOOKUP, SVTYPE_DETAILS } from '../../../utils/constants'

const LargeText = styled.div`
  font-size: 1.2em;
`

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
  pos: PropTypes.oneOf(PropTypes.string, PropTypes.number),
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
  SMALL_INTRON: { title: 'Small Intron', message: 'The LoF falls in a transcript whose exon/intron boundaries are undefined in the EnsEMBL API' },
  NON_CAN_SPLICE: { title: 'Non Canonical Splicing', message: 'This variant falls in a non-canonical splice site (not GT..AG)' },
  NON_CAN_SPLICE_SURR: { title: 'Non Canonical Splicing', message: 'This exon has surrounding splice sites that are non-canonical (not GT..AG)' },
  ANC_ALLELE: { title: 'Ancestral Allele', message: 'The alternate allele reverts the sequence back to the ancestral state' },
}

const addDividedLink = (links, name, href) => links.push((
  <span key={`divider-${name}`}>
    <HorizontalSpacer width={5} />
    |
    <HorizontalSpacer width={5} />
  </span>
), <a key={name} href={href} target="_blank" rel="noreferrer">{name}</a>)

const BaseSearchLinks = React.memo(({ variant, mainTranscript, genesById }) => {
  const links = []
  const mainGene = genesById[mainTranscript.geneId]
  let geneNames
  const variations = []

  if (mainGene) {
    geneNames = [mainGene.geneSymbol, ...getOtherGeneNames(mainGene)]

    if (variant.ref) {
      variations.unshift(
        `${variant.pos}${variant.ref}/${variant.alt}`, // 179432185A/G
        `${variant.pos}${variant.ref}>${variant.alt}`, // 179432185A>G
        `g.${variant.pos}${variant.ref}>${variant.alt}`, // g.179432185A>G
      )
    }

    if (mainTranscript.hgvsp) {
      const hgvsp = mainTranscript.hgvsp.split(':')[1].replace('p.', '')
      variations.unshift(
        `p.${hgvsp}`,
        hgvsp,
      )
    }

    if (mainTranscript.hgvsc) {
      const hgvsc = mainTranscript.hgvsc.split(':')[1].replace('c.', '')
      variations.unshift(
        `c.${hgvsc}`, // c.1282C>T
        hgvsc, // 1282C>T
        (`c.${hgvsc}`).replace('>', '/'), // c.1282C/T
        hgvsc.replace('>', '/'), // 1282C/T
      )
    }
  } else {
    geneNames = Object.keys(variant.transcripts || {}).reduce((acc, geneId) => {
      const gene = genesById[geneId]
      if (gene) {
        return [gene.geneSymbol, ...getOtherGeneNames(gene), ...acc]
      }
      return acc
    }, [])
  }

  if (geneNames && geneNames.length) {
    let pubmedSearch = `(${geneNames.join(' OR ')})`
    if (variations.length) {
      pubmedSearch = `${pubmedSearch} AND ( ${variations.join(' OR ')})`
      addDividedLink(links, 'google', `https://www.google.com/search?q=(${geneNames.join('|')})+(${variations.join('|')}`)
    }

    addDividedLink(links, 'pubmed', `https://www.ncbi.nlm.nih.gov/pubmed?term=${pubmedSearch}`)
  }

  const seqrLinkProps = { genomeVersion: variant.genomeVersion, svType: variant.svType }
  if (variant.svType) {
    if (variant.endChrom && variant.endChrom !== variant.chrom) {
      seqrLinkProps.location = `${variant.chrom}:${variant.pos - 50}-${variant.pos + 50}`
    } else {
      seqrLinkProps.location = `${variant.chrom}:${variant.pos}-${variant.end}%20`
    }

    const useLiftover = variant.liftedOverGenomeVersion === GENOME_VERSION_37
    if (variant.genomeVersion === GENOME_VERSION_37 || (useLiftover && variant.liftedOverPos)) {
      const endOffset = variant.endChrom ? 0 : variant.end - variant.pos
      const start = useLiftover ? variant.liftedOverPos : variant.pos
      const region = `${variant.chrom}-${start}-${start + endOffset}`
      addDividedLink(links, 'gnomad', `https://gnomad.broadinstitute.org/region/${region}?dataset=gnomad_sv_r2_1`)
    }
  } else {
    seqrLinkProps.variantId = variant.variantId
  }
  links.unshift(
    <Popup
      key="seqr-search"
      trigger={<SearchResultsLink key="seqr" buttonText="seqr" {...seqrLinkProps} />}
      content={`Search for this variant across all your seqr projects${variant.svType ? '. Any structural variant with ≥20% reciprocal overlap will be returned.' : ''}`}
      size="tiny"
    />,
  )

  return links
})

BaseSearchLinks.propTypes = {
  variant: PropTypes.object,
  mainTranscript: PropTypes.object,
  genesById: PropTypes.object,
}

const mapStateToProps = state => ({
  genesById: getGenesById(state),
})

const SearchLinks = connect(mapStateToProps)(BaseSearchLinks)

const BaseVariantLocusListLabels = React.memo(({ locusListIntervalsByProject, familiesByGuid, variant }) => {
  if (!locusListIntervalsByProject || locusListIntervalsByProject.length < 1) {
    return null
  }
  const { pos, end, genomeVersion, liftedOverPos, familyGuids = [] } = variant
  const locusListIntervals = familyGuids.reduce((acc, familyGuid) => ([
    ...acc, ...(locusListIntervalsByProject[familiesByGuid[familyGuid].projectGuid] || [])]), [])
  if (locusListIntervals.length < 1) {
    return null
  }
  const locusListGuids = locusListIntervals.filter((interval) => {
    const variantPos = genomeVersion === interval.genomeVersion ? pos : liftedOverPos
    if (!variantPos) {
      return false
    }
    if ((variantPos >= interval.start) && (variantPos <= interval.end)) {
      return true
    }
    if (end && !variant.endChrom) {
      const variantPosEnd = variantPos + (end - pos)
      return (variantPosEnd >= interval.start) && (variantPosEnd <= interval.end)
    }
    return false
  }).map(({ locusListGuid }) => locusListGuid)

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

  const lofDetails = (mainTranscript.lof === 'LC' || mainTranscript.lofFlags === 'NAGNAG_SITE') ? [
    ...(mainTranscript.lofFilter ? [...new Set(mainTranscript.lofFilter.split(/&|,/g))] : []).map((lofFilterKey) => {
      const lofFilter = LOF_FILTER_MAP[lofFilterKey] || { message: lofFilterKey }
      return (
        <div key={lofFilterKey}>
          <b>{`LOFTEE: ${lofFilter.title}`}</b>
          <br />
          {lofFilter.message}
        </div>
      )
    }),
    mainTranscript.lofFlags === 'NAGNAG_SITE' ? (
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

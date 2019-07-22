import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Label, Icon } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import SearchResultsLink from '../../buttons/SearchResultsLink'
import Modal from '../../modal/Modal'
import { ButtonLink } from '../../StyledComponents'
import Transcripts, { TranscriptLink } from './Transcripts'
import { LocusListLabels } from './VariantGene'
import { GENOME_VERSION_37 } from '../../../utils/constants'


const SequenceContainer = styled.span`
  word-break: break-all;
  color: ${props => props.color || 'inherit'};
`

const LargeText = styled.div`
  font-size: 1.2em;
`

export const getLocus = (chrom, pos, rangeSize) =>
  `chr${chrom}:${pos - rangeSize}-${pos + rangeSize}`

const UcscBrowserLink = ({ variant, useLiftover }) => {
  const chrom = useLiftover ? variant.liftedOverChrom : variant.chrom
  const pos = parseInt(useLiftover ? variant.liftedOverPos : variant.pos, 10)
  let genomeVersion = useLiftover ? variant.liftedOverGenomeVersion : variant.genomeVersion
  genomeVersion = genomeVersion === GENOME_VERSION_37 ? '19' : genomeVersion

  const highlight = `hg${genomeVersion}.chr${chrom}:${pos}-${pos + (variant.ref.length - 1)}`
  const position = getLocus(chrom, pos, 10)

  return (
    <a href={`http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg${genomeVersion}&highlight=${highlight}&position=${position}`} target="_blank">
      {chrom}:{pos}
    </a>
  )
}

UcscBrowserLink.propTypes = {
  variant: PropTypes.object,
  useLiftover: PropTypes.bool,
}

const MAX_SEQUENCE_LENGTH = 30
const SEQUENCE_POPUP_STYLE = { wordBreak: 'break-all' }

const Sequence = ({ sequence, ...props }) =>
  <SequenceContainer {...props}>
    {sequence.length > MAX_SEQUENCE_LENGTH ?
      <Popup trigger={<span>{`${sequence.substring(0, MAX_SEQUENCE_LENGTH)}...`}</span>} content={sequence} style={SEQUENCE_POPUP_STYLE} /> :
      sequence
    }
  </SequenceContainer>

Sequence.propTypes = {
  sequence: PropTypes.string.isRequired,
}

export const parseHgvs = hgvs => (hgvs || '').split(':').pop()

export const ProteinSequence = ({ hgvs }) =>
  <Sequence color="black" sequence={parseHgvs(hgvs)} />

ProteinSequence.propTypes = {
  hgvs: PropTypes.string.isRequired,
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

const annotationVariations = (mainTranscript, variant) => {
  const variations = []
  if (mainTranscript.hgvsc) {
    const hgvsc = mainTranscript.hgvsc.split(':')[1].replace('c.', '')
    variations.push(
      `${mainTranscript.geneSymbol}:c.${hgvsc}`, //TTN:c.78674T>C
      `c.${hgvsc}`, //c.1282C>T
      hgvsc, //1282C>T
      hgvsc.replace('>', '->'), //1282C->T
      hgvsc.replace('>', '-->'), //1282C-->T
      (`c.${hgvsc}`).replace('>', '/'), //c.1282C/T
      hgvsc.replace('>', '/'), //1282C/T
      `${mainTranscript.geneSymbol}:${hgvsc}`, //TTN:78674T>C
    )
  }

  if (mainTranscript.hgvsp) {
    const hgvsp = mainTranscript.hgvsp.split(':')[1].replace('p.', '')
    variations.push(
      `${mainTranscript.geneSymbol}:p.${hgvsp}`, //TTN:p.Ile26225Thr
      `${mainTranscript.geneSymbol}:${hgvsp}`, //TTN:Ile26225Thr
    )
  }

  if (variant.alt && variant.ref && variant.pos) {
    variations.push(
      `${variant.pos}${variant.ref}->${variant.alt}`, //179432185A->G
      `${variant.pos}${variant.ref}-->${variant.alt}`, //179432185A-->G
      `${variant.pos}${variant.ref}/${variant.alt}`, //179432185A/G
      `${variant.pos}${variant.ref}>${variant.alt}`, //179432185A>G
      `g.${variant.pos}${variant.ref}>${variant.alt}`, //g.179432185A>G
    )
  }

  return variations
}

const Annotations = ({ variant }) => {
  const { mainTranscript, rsid } = variant

  const variations = annotationVariations(mainTranscript, variant)
  const lofDetails = (mainTranscript.lof === 'LC' || mainTranscript.lofFlags === 'NAGNAG_SITE') ? [
    ...[...new Set(mainTranscript.lofFilter.split(/&|,/g))].map((lofFilterKey) => {
      const lofFilter = LOF_FILTER_MAP[lofFilterKey] || { message: lofFilterKey }
      return <div key={lofFilterKey}><b>LOFTEE: {lofFilter.title}</b><br />{lofFilter.message}.</div>
    }),
    mainTranscript.lofFlags === 'NAGNAG_SITE' ?
      <div key="NAGNAG_SITE">LOFTEE: <b>NAGNAG site</b>This acceptor site is rescued by another adjacent in-frame acceptor site.</div>
      : null,
  ] : null

  const transcriptPopupProps = {
    content: <TranscriptLink variant={variant} transcript={mainTranscript} />,
    size: 'mini',
    hoverable: true,
  }

  return (
    <div>
      { mainTranscript.majorConsequence &&
        <Modal
          modalName={`${variant.variantId}-annotations`}
          title="Transcripts"
          size="large"
          trigger={<ButtonLink>{mainTranscript.majorConsequence.replace(/_/g, ' ')}</ButtonLink>}
          popup={transcriptPopupProps}
        >
          <Transcripts variant={variant} />
        </Modal>
      }
      { lofDetails &&
        <span>
          <HorizontalSpacer width={12} />
          <Popup
            trigger={<Label color="red" horizontal size="tiny">LC LoF</Label>}
            content={lofDetails}
          />
        </span>
      }
      { mainTranscript.hgvsc &&
        <div>
          <b>HGVS.C</b><HorizontalSpacer width={5} /><ProteinSequence hgvs={mainTranscript.hgvsc} />
        </div>
      }
      { mainTranscript.hgvsp &&
        <div>
          <b>HGVS.P</b><HorizontalSpacer width={5} /><ProteinSequence hgvs={mainTranscript.hgvsp} />
        </div>
      }
      { Object.keys(mainTranscript).length > 0 && <VerticalSpacer height={10} />}
      <LargeText>
        <b><UcscBrowserLink variant={variant} /></b>
        <HorizontalSpacer width={10} />
        <Sequence sequence={variant.ref} />
        <Icon name="angle right" />
        <Sequence sequence={variant.alt} />
      </LargeText>
      {rsid &&
        <div>
          <a href={`http://www.ncbi.nlm.nih.gov/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=${rsid}`} target="_blank">
            {rsid}
          </a>
        </div>
      }
      {variant.liftedOverGenomeVersion === GENOME_VERSION_37 && (
        variant.liftedOverPos ?
          <div>
            hg19: <UcscBrowserLink variant={variant} useLiftover />
          </div>
          : <div>hg19: liftover failed</div>
        )
      }
      <VerticalSpacer height={5} />
      <LocusListLabels locusListGuids={variant.locusListGuids} />
      <VerticalSpacer height={5} />
      {mainTranscript.geneSymbol &&
        <div>
          <SearchResultsLink buttonText="seqr" variantId={variant.variantId} />
          <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
          <a href={`https://www.google.com/search?q=${mainTranscript.geneSymbol}+${variations.join('+')}`} target="_blank">
            google
          </a>
          <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
          <a href={`https://www.ncbi.nlm.nih.gov/pubmed?term=${mainTranscript.geneSymbol} AND ( ${variations.join(' OR ')})`} target="_blank">
            pubmed
          </a>
        </div>
      }
    </div>
  )
}

Annotations.propTypes = {
  variant: PropTypes.object,
}

export default Annotations
